"""
Crop Type Classifier
====================
USP 4.1: Foundation-Model-Powered Few-Shot Crop Classification

Instead of hand-engineered indices + large labelled datasets, we:
1. Generate per-pixel embeddings from a pretrained EO foundation model
   (Prithvi-EO-2.0 / Clay Foundation Model via HuggingFace).
2. Stack those embeddings with multi-temporal hand-crafted features.
3. Train a lightweight Random Forest / XGBoost classifier on top.

This reaches strong accuracy with far fewer ground-truth labels — directly
solving the "ground truth is scarce" problem in operational crop mapping.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Crop class labels used in the pilot command area
CROP_CLASSES = {
    0: "non_crop",
    1: "paddy_rice",
    2: "wheat",
    3: "sugarcane",
    4: "cotton",
    5: "maize",
    6: "groundnut",
    7: "vegetables",
    8: "fallow",
}

# Colour palette for map rendering (hex)
CROP_PALETTE = {
    0: "#6B7280",  # non_crop — grey
    1: "#22C55E",  # paddy_rice — green
    2: "#EAB308",  # wheat — amber
    3: "#A78BFA",  # sugarcane — violet
    4: "#F97316",  # cotton — orange
    5: "#84CC16",  # maize — lime
    6: "#FB923C",  # groundnut — peach
    7: "#34D399",  # vegetables — emerald
    8: "#D1D5DB",  # fallow — light grey
}


# ---------------------------------------------------------------------------
# Foundation model embedding hook (USP 4.1)
# ---------------------------------------------------------------------------

class FoundationModelEmbedder:
    """
    Generates per-pixel/parcel embeddings from a pretrained EO foundation model.

    Supported backbones:
    - 'prithvi'  : NASA-IBM Prithvi-EO-2.0 (HuggingFace hub)
    - 'clay'     : Clay Foundation Model (open weights)
    - 'mock'     : Returns random embeddings for demo / CI (no GPU needed)

    In production, load the model weights from HuggingFace and run inference
    on the multi-temporal spectral stack. The 256-dim embedding captures
    global crop-phenology structure learned from large EO datasets, so a
    lightweight classifier on top reaches high accuracy with few labels.
    """

    EMBEDDING_DIM = 256

    def __init__(self, backbone: str = "mock"):
        self.backbone = backbone
        self._model = None
        logger.info("FoundationModelEmbedder initialized with backbone: %s", backbone)

        if backbone == "prithvi":
            self._load_prithvi()
        elif backbone == "clay":
            self._load_clay()
        # 'mock' requires no loading

    def _load_prithvi(self):
        """Load NASA-IBM Prithvi-EO-2.0 from HuggingFace."""
        try:
            from transformers import AutoModel  # type: ignore
            logger.info("Loading Prithvi-EO-2.0 from HuggingFace hub...")
            self._model = AutoModel.from_pretrained(
                "ibm-nasa-geospatial/Prithvi-EO-2.0-300M",
                trust_remote_code=True,
            )
            logger.info("Prithvi-EO-2.0 loaded successfully.")
        except Exception as e:
            logger.warning("Could not load Prithvi-EO-2.0: %s. Falling back to mock.", e)
            self.backbone = "mock"

    def _load_clay(self):
        """Load Clay Foundation Model from HuggingFace."""
        try:
            from transformers import AutoModel  # type: ignore
            logger.info("Loading Clay Foundation Model from HuggingFace hub...")
            self._model = AutoModel.from_pretrained(
                "made-with-clay/Clay",
                trust_remote_code=True,
            )
            logger.info("Clay model loaded successfully.")
        except Exception as e:
            logger.warning("Could not load Clay model: %s. Falling back to mock.", e)
            self.backbone = "mock"

    def embed(self, spectral_stack: np.ndarray) -> np.ndarray:
        """
        Generate embeddings for a spatial patch.

        Parameters
        ----------
        spectral_stack : (T, C, H, W) — T time steps, C channels, H×W pixels

        Returns
        -------
        embeddings : (H * W, EMBEDDING_DIM) — one embedding per pixel
        """
        T, C, H, W = spectral_stack.shape
        n_pixels = H * W

        if self.backbone == "mock":
            # Reproducible mock embeddings for demo (seeded on spatial mean)
            seed = int(spectral_stack.mean() * 1000) % 2**31
            rng = np.random.default_rng(seed)
            return rng.standard_normal((n_pixels, self.EMBEDDING_DIM)).astype(np.float32)

        # Real inference path (Prithvi / Clay)
        import torch  # type: ignore
        with torch.no_grad():
            tensor = torch.tensor(spectral_stack, dtype=torch.float32).unsqueeze(0)  # (1, T, C, H, W)
            out = self._model(tensor)
            # Extract pixel-level embeddings — shape depends on model head
            emb = out.last_hidden_state.squeeze(0).reshape(n_pixels, -1).cpu().numpy()
            if emb.shape[-1] != self.EMBEDDING_DIM:
                # Project to standard dim if needed
                proj = np.random.randn(emb.shape[-1], self.EMBEDDING_DIM).astype(np.float32)
                emb = emb @ proj
            return emb


# ---------------------------------------------------------------------------
# Crop classifier
# ---------------------------------------------------------------------------

class CropClassifier:
    """
    Lightweight crop-type classifier combining:
    - Foundation-model embeddings (256-dim)
    - Hand-crafted multi-temporal spectral features (14-dim)

    Classifier: XGBoost / Random Forest (Scikit-learn compatible API).
    """

    def __init__(
        self,
        embedder_backbone: str = "mock",
        classifier_type: str = "xgboost",
        model_path: Optional[Path] = None,
    ):
        self.embedder = FoundationModelEmbedder(backbone=embedder_backbone)
        self.classifier_type = classifier_type
        self._clf = None

        if model_path and Path(model_path).exists():
            self.load(model_path)
        else:
            self._init_classifier()

    def _init_classifier(self):
        if self.classifier_type == "xgboost":
            try:
                from xgboost import XGBClassifier  # type: ignore
                self._clf = XGBClassifier(
                    n_estimators=300,
                    max_depth=6,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    use_label_encoder=False,
                    eval_metric="mlogloss",
                    random_state=42,
                    n_jobs=-1,
                )
                logger.info("XGBoost classifier initialized.")
            except ImportError:
                logger.warning("XGBoost not available; falling back to Random Forest.")
                self.classifier_type = "rf"

        if self.classifier_type == "rf":
            from sklearn.ensemble import RandomForestClassifier  # type: ignore
            self._clf = RandomForestClassifier(
                n_estimators=200,
                max_depth=None,
                min_samples_leaf=5,
                n_jobs=-1,
                random_state=42,
            )
            logger.info("Random Forest classifier initialized.")

    def _prepare_features(
        self,
        spectral_stack: np.ndarray,   # (T, C, H, W)
        feature_cube: np.ndarray,      # (H, W, 14)
    ) -> np.ndarray:
        """Combine foundation embeddings + hand-crafted features → (N, D) matrix."""
        H, W = feature_cube.shape[:2]
        embeddings = self.embedder.embed(spectral_stack)                         # (N, 256)
        hand_crafted = feature_cube.reshape(H * W, -1)                          # (N, 14)
        return np.concatenate([embeddings, hand_crafted], axis=1)                # (N, 270)

    def train(
        self,
        spectral_stack: np.ndarray,
        feature_cube: np.ndarray,
        labels: np.ndarray,           # (H * W,) integer class IDs
    ) -> Dict[str, float]:
        """
        Train the classifier.

        Returns
        -------
        dict with 'train_accuracy' and 'n_samples'
        """
        from sklearn.metrics import accuracy_score  # type: ignore

        X = self._prepare_features(spectral_stack, feature_cube)
        mask = labels >= 0  # exclude unlabelled pixels (-1)
        X_train, y_train = X[mask], labels.ravel()[mask]

        logger.info("Training %s on %d labelled pixels...", self.classifier_type, len(y_train))
        self._clf.fit(X_train, y_train)

        y_pred = self._clf.predict(X_train)
        acc = accuracy_score(y_train, y_pred)
        logger.info("Train accuracy: %.3f", acc)
        return {"train_accuracy": float(acc), "n_samples": int(len(y_train))}

    def predict(
        self,
        spectral_stack: np.ndarray,
        feature_cube: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict crop classes and class probabilities for all pixels.

        Returns
        -------
        class_map  : (H, W) integer array of predicted class IDs
        prob_map   : (H, W, n_classes) probability array
        """
        H, W = feature_cube.shape[:2]

        if self._clf is None:
            logger.warning("No trained model; returning demo predictions.")
            return self._demo_prediction(H, W)

        X = self._prepare_features(spectral_stack, feature_cube)
        class_ids = self._clf.predict(X).reshape(H, W)
        probs = self._clf.predict_proba(X).reshape(H, W, -1)
        return class_ids, probs

    def _demo_prediction(self, H: int, W: int) -> Tuple[np.ndarray, np.ndarray]:
        """Return plausible-looking demo predictions without a trained model."""
        rng = np.random.default_rng(123)
        # Create spatially coherent blobs using a simple distance approach
        n_classes = len(CROP_CLASSES)
        class_map = np.zeros((H, W), dtype=np.int32)

        # Assign regions to crop classes in a grid pattern
        stripe_height = max(1, H // n_classes)
        for i, cid in enumerate(CROP_CLASSES.keys()):
            row_start = i * stripe_height
            row_end = min((i + 1) * stripe_height, H)
            class_map[row_start:row_end, :] = cid

        # Add noise
        noise_mask = rng.random((H, W)) < 0.15
        class_map[noise_mask] = rng.integers(0, n_classes, size=noise_mask.sum())

        # Uniform probability for demo
        probs = np.ones((H, W, n_classes)) / n_classes
        return class_map, probs

    def save(self, path: Path):
        with open(path, "wb") as f:
            pickle.dump(self._clf, f)
        logger.info("Model saved to %s", path)

    def load(self, path: Path):
        with open(path, "rb") as f:
            self._clf = pickle.load(f)
        logger.info("Model loaded from %s", path)
