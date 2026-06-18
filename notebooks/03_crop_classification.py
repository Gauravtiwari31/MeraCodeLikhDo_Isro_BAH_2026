"""
Notebook 03 — Crop Classification
====================================
Foundation Model Embeddings + XGBoost / Random Forest
USP 4.1: Few-Shot Crop Classification
"""

import sys, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
sys.path.insert(0, str(Path('../backend').resolve()))

from app.models.crop_classifier import (
    CropClassifier, CROP_CLASSES, CROP_PALETTE,
    FoundationModelEmbedder
)
from app.pipeline.feature_engineering import (
    compute_ndvi, compute_evi, compute_ndwi, build_feature_cube
)

# ── Simulate multi-temporal data ─────────────────────────────────────
H, W, T = 30, 30, 20
rng = np.random.default_rng(42)

nir_s  = rng.uniform(0.2, 0.6, (T, H, W))
red_s  = rng.uniform(0.05, 0.2, (T, H, W))
green_s= rng.uniform(0.05, 0.15, (T, H, W))
blue_s = rng.uniform(0.02, 0.08, (T, H, W))
vv_s   = rng.uniform(-20, -8, (T, H, W))
vh_s   = rng.uniform(-28, -12, (T, H, W))

# Seasonal signal
t_arr = np.linspace(0, 1, T)
for t in range(T):
    peak = 0.45 * np.exp(-((t_arr[t] - 0.55)**2) / (2 * 0.05))
    nir_s[t] += peak
    red_s[t]  -= peak * 0.3

ndvi_s = compute_ndvi(nir_s, red_s)
evi_s  = compute_evi(nir_s, red_s, blue_s)
ndwi_s = compute_ndwi(green_s, nir_s)

ndvi_min = ndvi_s.min(axis=0)
ndvi_max = ndvi_s.max(axis=0)

feature_cube = build_feature_cube(ndvi_s, evi_s, ndwi_s, vv_s, vh_s, ndvi_min, ndvi_max)
spectral_stack = np.stack([nir_s, red_s, green_s, vv_s, vh_s], axis=1)  # (T, C, H, W)

# ── Foundation Model Embeddings (mock backbone) ──────────────────────
print("=== Foundation Model Embedder (Mock Mode) ===")
embedder = FoundationModelEmbedder(backbone="mock")
embeddings = embedder.embed(spectral_stack)
print(f"Embedding shape: {embeddings.shape}  (pixels × dim)")
print(f"Embedding dim:   {embedder.EMBEDDING_DIM}")
print("\nIn production: backbone='prithvi' uses NASA-IBM Prithvi-EO-2.0")
print("from HuggingFace — captures global land-cover structure for few-shot accuracy.\n")

# ── Train crop classifier ─────────────────────────────────────────────
print("=== Crop Classifier (XGBoost + Foundation Embeddings) ===")
clf = CropClassifier(embedder_backbone="mock", classifier_type="xgboost")

# Simulated ground-truth labels (partial labels — few-shot scenario)
labels = np.full(H * W, -1)   # -1 = unlabelled
labelled_idx = rng.choice(H * W, size=120, replace=False)  # 120 / 900 pixels labelled
ground_truth_class = rng.choice([1, 4, 2, 5, 8], size=120, p=[0.40, 0.20, 0.15, 0.15, 0.10])
labels[labelled_idx] = ground_truth_class

metrics = clf.train(spectral_stack, feature_cube, labels)
print(f"Training samples: {metrics['n_samples']}")
print(f"Train accuracy:   {metrics['train_accuracy']:.3f} ({metrics['train_accuracy']*100:.1f}%)")

# ── Inference ─────────────────────────────────────────────────────────
class_map, prob_map = clf.predict(spectral_stack, feature_cube)
print(f"\nPredicted class map shape: {class_map.shape}")
print(f"Probability map shape:    {prob_map.shape}")

# Area stats
print("\n=== Predicted Area per Crop ===")
pixel_ha = 0.09
for cid, cname in CROP_CLASSES.items():
    count = (class_map == cid).sum()
    print(f"  {cname:15s}: {count} px → {count*pixel_ha:.1f} ha")

# ── Visualize ─────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('Crop Classification — Foundation Embeddings + XGBoost\nUSP 4.1: Few-Shot Crop Classification | ISRO BAH 2026', fontsize=12)

# Build colour array
color_img = np.zeros((H, W, 3))
for cid, hex_color in CROP_PALETTE.items():
    r, g, b = int(hex_color[1:3],16)/255, int(hex_color[3:5],16)/255, int(hex_color[5:7],16)/255
    mask = class_map == cid
    color_img[mask] = [r, g, b]

axes[0].imshow(color_img)
axes[0].set_title('Predicted Crop Type Map')
axes[0].axis('off')

axes[1].imshow(ndvi_s[-1], cmap='RdYlGn', vmin=0, vmax=0.9)
axes[1].set_title('NDVI (last composite)')
axes[1].axis('off')

axes[2].imshow(prob_map.max(axis=-1), cmap='Blues', vmin=0, vmax=1)
axes[2].set_title('Max Class Probability\n(classifier confidence)')
axes[2].axis('off')

plt.tight_layout()
plt.savefig('03_crop_classification.png', dpi=150, bbox_inches='tight')
plt.close()
print('\nSaved: 03_crop_classification.png')
