"""
Feature Engineering
===================
Computes vegetation indices, SAR-derived features, GLCM texture, and
phenological metrics from analysis-ready optical and SAR data stacks.

Outputs a per-pixel feature cube used by the crop classifier, stress
detector, and water-deficit estimator.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vegetation indices (computed on numpy arrays for offline / demo path)
# ---------------------------------------------------------------------------

def compute_ndvi(nir: np.ndarray, red: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """
    Normalized Difference Vegetation Index.
    NDVI = (NIR - RED) / (NIR + RED)
    Range: [-1, 1]; healthy green vegetation typically > 0.3
    """
    return (nir - red) / (nir + red + eps)


def compute_evi(
    nir: np.ndarray,
    red: np.ndarray,
    blue: np.ndarray,
    G: float = 2.5,
    C1: float = 6.0,
    C2: float = 7.5,
    L: float = 1.0,
    eps: float = 1e-8,
) -> np.ndarray:
    """
    Enhanced Vegetation Index — less sensitive to atmospheric/soil noise.
    EVI = G * (NIR - RED) / (NIR + C1*RED - C2*BLUE + L)
    """
    return G * (nir - red) / (nir + C1 * red - C2 * blue + L + eps)


def compute_ndwi(green: np.ndarray, nir: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """
    Normalized Difference Water Index — moisture in vegetation canopy.
    NDWI = (GREEN - NIR) / (GREEN + NIR)
    """
    return (green - nir) / (green + nir + eps)


def compute_vci(ndvi: np.ndarray, ndvi_min: np.ndarray, ndvi_max: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """
    Vegetation Condition Index — NDVI normalized to multi-year historical range.
    VCI = (NDVI - NDVI_min) / (NDVI_max - NDVI_min)
    Values near 0 → severe stress; near 1 → optimal condition.
    """
    return (ndvi - ndvi_min) / (ndvi_max - ndvi_min + eps)


def compute_smi(vv: np.ndarray, vh: np.ndarray) -> np.ndarray:
    """
    Soil Moisture Index proxy from SAR backscatter.
    SMI = VH / VV ratio — sensitive to canopy moisture and roughness.
    """
    eps = 1e-8
    return vh / (vv + eps)


# ---------------------------------------------------------------------------
# SAR texture features (GLCM)
# ---------------------------------------------------------------------------

def compute_glcm_texture(sar_band: np.ndarray, window_size: int = 5) -> Dict[str, np.ndarray]:
    """
    Compute Grey-Level Co-occurrence Matrix texture features.
    Uses a sliding window approximation for contrast, homogeneity, energy.

    In production this would call the full GLCM via scikit-image;
    here we use fast approximations suitable for demo data.
    """
    from scipy.ndimage import uniform_filter, generic_filter

    # Normalize to 0-255 range
    sar_norm = ((sar_band - sar_band.min()) / (sar_band.max() - sar_band.min() + 1e-8) * 255).astype(np.float32)

    mean = uniform_filter(sar_norm, size=window_size)
    variance = uniform_filter(sar_norm**2, size=window_size) - mean**2
    contrast = np.sqrt(np.abs(variance))

    # Homogeneity proxy: inverse of local variance
    homogeneity = 1.0 / (1.0 + variance + 1e-8)

    return {
        "glcm_contrast": contrast,
        "glcm_homogeneity": homogeneity,
        "glcm_mean": mean,
    }


# ---------------------------------------------------------------------------
# Phenological metrics (Start of Season, Peak, Length of Growing Period)
# ---------------------------------------------------------------------------

def compute_phenometrics(
    ndvi_time_series: np.ndarray,
    dates: List[str],
    smoothing_window: int = 3,
) -> Dict[str, Any]:
    """
    Derive phenological metrics from a per-pixel NDVI time series.

    Parameters
    ----------
    ndvi_time_series : (T, H, W) array — NDVI for T time steps over H×W pixels
    dates            : list of T ISO date strings
    smoothing_window : window for Savitzky-Golay / running-mean smoothing

    Returns
    -------
    dict with keys:
        'sos_index'  — index of Start of Season (NDVI crosses 0.25 rising)
        'peak_index' — index of peak NDVI
        'eos_index'  — index of End of Season (NDVI drops below 0.25 falling)
        'lgp'        — Length of Growing Period in number of 8-day steps
        'current_stage' — inferred stage name for most recent date
    """
    T, H, W = ndvi_time_series.shape

    # Smooth the NDVI time series (spatial mean for demo)
    spatial_mean = ndvi_time_series.mean(axis=(1, 2))  # (T,)

    # Smooth with simple moving average
    kernel = np.ones(smoothing_window) / smoothing_window
    smoothed = np.convolve(spatial_mean, kernel, mode="same")

    # Detect SOS: first index where NDVI crosses above 0.25
    sos_threshold = 0.25
    sos_index = 0
    for i in range(1, T):
        if smoothed[i - 1] < sos_threshold and smoothed[i] >= sos_threshold:
            sos_index = i
            break

    # Peak: index of maximum NDVI
    peak_index = int(np.argmax(smoothed))

    # EOS: first index after peak where NDVI drops below 0.25
    eos_index = T - 1
    for i in range(peak_index, T):
        if smoothed[i] < sos_threshold:
            eos_index = i
            break

    lgp = max(0, eos_index - sos_index)

    # Infer current growth stage based on most recent composite index
    current_idx = T - 1
    if current_idx < sos_index:
        stage = "pre_sowing"
    elif current_idx <= sos_index + max(1, lgp // 4):
        stage = "sowing_emergence"
    elif current_idx <= sos_index + max(1, lgp // 2):
        stage = "vegetative"
    elif current_idx <= sos_index + max(1, 3 * lgp // 4):
        stage = "flowering_heading"
    else:
        stage = "maturity_harvest"

    return {
        "sos_index": sos_index,
        "sos_date": dates[sos_index] if sos_index < len(dates) else None,
        "peak_index": peak_index,
        "peak_date": dates[peak_index] if peak_index < len(dates) else None,
        "eos_index": eos_index,
        "lgp": lgp,
        "smoothed_ndvi": smoothed.tolist(),
        "current_stage": stage,
    }


def assign_growth_stage_per_pixel(
    ndvi_cube: np.ndarray,
    current_t: int,
) -> np.ndarray:
    """
    Assign a growth stage integer to each pixel based on temporal NDVI profile.

    Stage encoding:
        0 = pre_sowing
        1 = sowing_emergence
        2 = vegetative
        3 = flowering_heading
        4 = maturity_harvest

    Parameters
    ----------
    ndvi_cube : (T, H, W) NDVI time series
    current_t : index of the 'current' time step

    Returns
    -------
    stage_map : (H, W) integer array
    """
    T, H, W = ndvi_cube.shape

    ndvi_max = ndvi_cube.max(axis=0)          # (H, W)
    ndvi_current = ndvi_cube[current_t]        # (H, W)
    ndvi_peak_t = ndvi_cube.argmax(axis=0)     # (H, W) — time index of peak

    stage_map = np.zeros((H, W), dtype=np.uint8)

    # Pre-sowing: very low NDVI throughout
    stage_map[ndvi_max < 0.15] = 0

    # Vegetative: NDVI rising, current < peak
    rising = (ndvi_current > 0.15) & (current_t < ndvi_peak_t)
    stage_map[rising & (ndvi_current < 0.4)] = 1   # sowing/emergence
    stage_map[rising & (ndvi_current >= 0.4)] = 2  # vegetative

    # Flowering: near peak
    at_peak = np.abs(current_t - ndvi_peak_t) <= 1
    stage_map[at_peak & (ndvi_max > 0.3)] = 3

    # Maturity: past peak, declining
    declining = (ndvi_current > 0.1) & (current_t > ndvi_peak_t)
    stage_map[declining] = 4

    return stage_map


# ---------------------------------------------------------------------------
# Feature cube assembly
# ---------------------------------------------------------------------------

def build_feature_cube(
    ndvi_stack: np.ndarray,            # (T, H, W)
    evi_stack: np.ndarray,             # (T, H, W)
    ndwi_stack: np.ndarray,            # (T, H, W)
    vv_stack: np.ndarray,              # (T, H, W)
    vh_stack: np.ndarray,              # (T, H, W)
    ndvi_historical_min: np.ndarray,   # (H, W) multi-year min
    ndvi_historical_max: np.ndarray,   # (H, W) multi-year max
) -> np.ndarray:
    """
    Assemble the final (H, W, F) feature cube for ML inference.

    Features (F = 14):
        0  NDVI_mean           — temporal mean NDVI
        1  NDVI_std            — temporal std (phenology variability)
        2  EVI_mean            — mean EVI
        3  NDWI_mean           — mean NDWI
        4  VCI_mean            — mean Vegetation Condition Index
        5  VV_mean             — mean SAR VV backscatter
        6  VH_mean             — mean SAR VH backscatter
        7  VH_VV_ratio         — mean VH/VV ratio (moisture proxy)
        8  glcm_contrast_mean  — mean GLCM contrast over SAR VV
        9  glcm_homogeneity    — mean GLCM homogeneity
       10  ndvi_peak           — peak NDVI over the season
       11  ndvi_at_sos         — NDVI at start-of-season index
       12  lgp_proxy           — length of green period (scaled)
       13  stage_id            — current growth stage (0-4)
    """
    T, H, W = ndvi_stack.shape

    # Temporal aggregations
    ndvi_mean = ndvi_stack.mean(axis=0)
    ndvi_std  = ndvi_stack.std(axis=0)
    evi_mean  = evi_stack.mean(axis=0)
    ndwi_mean = ndwi_stack.mean(axis=0)
    vv_mean   = vv_stack.mean(axis=0)
    vh_mean   = vh_stack.mean(axis=0)
    vh_vv     = compute_smi(vv_mean, vh_mean)

    vci_mean  = compute_vci(ndvi_mean, ndvi_historical_min, ndvi_historical_max)

    # SAR texture on time-averaged VV
    glcm = compute_glcm_texture(vv_mean)

    ndvi_peak   = ndvi_stack.max(axis=0)
    sos_idx     = np.argmax(ndvi_stack > 0.25, axis=0).astype(np.float32) / max(T, 1)
    lgp_proxy   = (ndvi_stack > 0.25).sum(axis=0).astype(np.float32) / max(T, 1)
    stage_map   = assign_growth_stage_per_pixel(ndvi_stack, current_t=T - 1).astype(np.float32)

    cube = np.stack([
        ndvi_mean,
        ndvi_std,
        evi_mean,
        ndwi_mean,
        vci_mean,
        vv_mean,
        vh_mean,
        vh_vv,
        glcm["glcm_contrast"],
        glcm["glcm_homogeneity"],
        ndvi_peak,
        sos_idx,
        lgp_proxy,
        stage_map,
    ], axis=-1)  # (H, W, 14)

    logger.info(
        "Feature cube assembled: shape=%s, features=%d", cube.shape, cube.shape[-1]
    )
    return cube
