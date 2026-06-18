"""
Phenology-Aware Moisture Stress Detector
=========================================
USP 4.2: True Stage-Level Optical–SAR Fusion (not just gap-filling)

Fuses VV/VH SAR backscatter and texture with optical indices (NDVI anomaly,
NDWI, VCI) at the level of each phenological stage:
    sowing_emergence → vegetative → flowering_heading → maturity_harvest

The resulting stress index is STAGE-AWARE — the same VCI value means
something different at sowing versus flowering — giving agronomically
meaningful (not just statistically smoothed) output.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stage-wise stress thresholds
# Each growth stage has different sensitivity to water stress, so we use
# different VCI / SAR fusion weights per stage.
# ---------------------------------------------------------------------------

STAGE_CONFIG: Dict[str, Dict] = {
    "pre_sowing": {
        "vci_thresholds": {"severe": 0.15, "moderate": 0.30, "mild": 0.50},
        "sar_weight": 0.2,
        "optical_weight": 0.8,
        "description": "Pre-sowing period — baseline moisture assessment.",
    },
    "sowing_emergence": {
        "vci_thresholds": {"severe": 0.20, "moderate": 0.35, "mild": 0.55},
        "sar_weight": 0.4,   # SAR more important — optical NDVI low at emergence
        "optical_weight": 0.6,
        "description": "Sowing to 30 DAE — establishment stress highly damaging.",
    },
    "vegetative": {
        "vci_thresholds": {"severe": 0.25, "moderate": 0.40, "mild": 0.60},
        "sar_weight": 0.3,
        "optical_weight": 0.7,
        "description": "Vegetative stage — canopy development; moderate sensitivity.",
    },
    "flowering_heading": {
        "vci_thresholds": {"severe": 0.30, "moderate": 0.45, "mild": 0.65},
        "sar_weight": 0.25,
        "optical_weight": 0.75,
        "description": "Flowering/heading — most sensitive stage; stress causes yield loss.",
    },
    "maturity_harvest": {
        "vci_thresholds": {"severe": 0.15, "moderate": 0.25, "mild": 0.40},
        "sar_weight": 0.5,   # Optical NDVI declining; SAR carries more signal
        "optical_weight": 0.5,
        "description": "Maturity — grain filling; some stress acceptable.",
    },
}

STRESS_CLASSES = {
    0: "no_stress",
    1: "mild_stress",
    2: "moderate_stress",
    3: "severe_stress",
}

STRESS_PALETTE = {
    0: "#22C55E",  # green
    1: "#FDE047",  # yellow
    2: "#F97316",  # orange
    3: "#EF4444",  # red
}


# ---------------------------------------------------------------------------
# Core stress detection
# ---------------------------------------------------------------------------

def compute_ndvi_anomaly(
    ndvi_current: np.ndarray,
    ndvi_historical_mean: np.ndarray,
    ndvi_historical_std: np.ndarray,
    eps: float = 1e-8,
) -> np.ndarray:
    """
    Standardized NDVI anomaly relative to multi-year historical baseline.
    Anomaly = (NDVI_current - NDVI_mean) / NDVI_std

    Negative anomaly → below-average vegetation condition (stress signal).
    """
    return (ndvi_current - ndvi_historical_mean) / (ndvi_historical_std + eps)


def compute_stage_aware_stress_index(
    vci: np.ndarray,
    ndwi: np.ndarray,
    smi: np.ndarray,           # SAR-derived soil moisture index (VH/VV)
    ndvi_anomaly: np.ndarray,
    stage_map: np.ndarray,     # (H, W) int 0-4 — growth stage per pixel
) -> np.ndarray:
    """
    Compute a fused, stage-weighted stress index for each pixel.

    The index blends:
      - VCI (optical vegetation condition)
      - NDWI (canopy moisture)
      - SMI (SAR-derived moisture proxy)
      - NDVI anomaly (deviation from historical baseline)

    Weights vary per phenological stage (USP 4.2).

    Returns
    -------
    stress_index : (H, W) float in [0, 1] — 0 = no stress, 1 = severe stress
    """
    H, W = vci.shape
    stress_index = np.zeros((H, W), dtype=np.float32)

    stage_names = {0: "pre_sowing", 1: "sowing_emergence", 2: "vegetative",
                   3: "flowering_heading", 4: "maturity_harvest"}

    for stage_id, stage_name in stage_names.items():
        mask = stage_map == stage_id
        if not mask.any():
            continue

        cfg = STAGE_CONFIG[stage_name]
        opt_w = cfg["optical_weight"]
        sar_w = cfg["sar_weight"]

        # Optical stress component: invert VCI and combine with NDWI anomaly
        # VCI near 0 → high stress; near 1 → no stress
        optical_stress = np.clip(1.0 - vci[mask], 0, 1)

        # NDWI contribution: negative NDWI anomaly indicates canopy dryness
        ndwi_stress = np.clip(-ndwi[mask], 0, 1)

        # SAR moisture contribution: low SMI → dry soil/canopy
        sar_stress = np.clip(1.0 - smi[mask], 0, 1)

        # NDVI anomaly: convert to [0,1] stress component
        anomaly_stress = np.clip(-ndvi_anomaly[mask] / 2.0, 0, 1)

        # Stage-weighted fusion
        fused = (
            opt_w * 0.6 * optical_stress
            + opt_w * 0.4 * ndwi_stress
            + sar_w * 0.7 * sar_stress
            + sar_w * 0.3 * anomaly_stress
        )
        stress_index[mask] = np.clip(fused, 0, 1)

    return stress_index


def classify_stress_severity(
    stress_index: np.ndarray,
    stage_map: np.ndarray,
) -> np.ndarray:
    """
    Convert continuous stress index to categorical severity class per pixel,
    using stage-specific thresholds.

    Returns
    -------
    severity_map : (H, W) int — 0=no_stress, 1=mild, 2=moderate, 3=severe
    """
    H, W = stress_index.shape
    severity_map = np.zeros((H, W), dtype=np.uint8)

    stage_names = {0: "pre_sowing", 1: "sowing_emergence", 2: "vegetative",
                   3: "flowering_heading", 4: "maturity_harvest"}

    for stage_id, stage_name in stage_names.items():
        mask = stage_map == stage_id
        if not mask.any():
            continue

        cfg = STAGE_CONFIG[stage_name]["vci_thresholds"]
        idx = stress_index[mask]

        sev = np.zeros(idx.shape, dtype=np.uint8)
        sev[idx >= cfg["mild"]] = 1       # mild stress
        sev[idx >= cfg["moderate"]] = 2   # moderate
        sev[idx >= cfg["severe"]] = 3     # severe
        severity_map[mask] = sev

    return severity_map


# ---------------------------------------------------------------------------
# Monte Carlo uncertainty quantification (USP 4.3)
# ---------------------------------------------------------------------------

def mc_dropout_stress_uncertainty(
    stress_index_samples: List[np.ndarray],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    USP 4.3: Confidence-Aware Advisory Engine.

    Given N Monte Carlo samples of the stress index (obtained by running the
    model N times with dropout enabled), compute:
    - mean stress index
    - uncertainty (std of samples) — high std → low confidence

    Parameters
    ----------
    stress_index_samples : list of (H, W) arrays — N MC samples

    Returns
    -------
    mean_stress   : (H, W) float
    uncertainty   : (H, W) float — 0 = fully confident, 1 = highly uncertain
    """
    stack = np.stack(stress_index_samples, axis=0)  # (N, H, W)
    mean_stress = stack.mean(axis=0)
    uncertainty = stack.std(axis=0)
    return mean_stress, uncertainty


def compute_confidence_flag(
    uncertainty: np.ndarray,
    low_threshold: float = 0.05,
    high_threshold: float = 0.15,
) -> np.ndarray:
    """
    Convert per-pixel uncertainty to a categorical confidence flag.

    Returns
    -------
    flag_map : (H, W) int
        0 = HIGH confidence (uncertainty < low_threshold)
        1 = MEDIUM confidence
        2 = LOW confidence — ground verification recommended (USP 4.3)
    """
    flag = np.zeros(uncertainty.shape, dtype=np.uint8)
    flag[uncertainty >= low_threshold] = 1
    flag[uncertainty >= high_threshold] = 2
    return flag


# ---------------------------------------------------------------------------
# High-level convenience function
# ---------------------------------------------------------------------------

def detect_stress(
    ndvi_current: np.ndarray,
    ndwi_current: np.ndarray,
    vci: np.ndarray,
    smi: np.ndarray,
    ndvi_anomaly: np.ndarray,
    stage_map: np.ndarray,
    n_mc_samples: int = 20,
    mc_noise_std: float = 0.02,
) -> Dict[str, np.ndarray]:
    """
    Full stress detection pipeline for one 8-day composite.

    Runs N Monte Carlo passes (via input perturbation for demo;
    in production use MC Dropout on a deep model) to produce
    uncertainty estimates alongside the stress prediction.

    Returns
    -------
    dict with keys:
        'stress_index'    (H, W) float
        'severity_map'    (H, W) int 0-3
        'uncertainty'     (H, W) float
        'confidence_flag' (H, W) int 0-2
        'stage_map'       (H, W) int 0-4
    """
    rng = np.random.default_rng(42)
    samples = []

    for _ in range(n_mc_samples):
        # Perturb inputs slightly to simulate MC Dropout uncertainty
        _vci   = vci   + rng.normal(0, mc_noise_std, vci.shape)
        _smi   = smi   + rng.normal(0, mc_noise_std, smi.shape)
        _ndwi  = ndwi_current + rng.normal(0, mc_noise_std, ndwi_current.shape)
        _anom  = ndvi_anomaly + rng.normal(0, mc_noise_std, ndvi_anomaly.shape)

        si = compute_stage_aware_stress_index(_vci, _ndwi, _smi, _anom, stage_map)
        samples.append(si)

    mean_stress, uncertainty = mc_dropout_stress_uncertainty(samples)
    severity_map = classify_stress_severity(mean_stress, stage_map)
    confidence_flag = compute_confidence_flag(uncertainty)

    return {
        "stress_index":    mean_stress,
        "severity_map":    severity_map,
        "uncertainty":     uncertainty,
        "confidence_flag": confidence_flag,
        "stage_map":       stage_map,
    }
