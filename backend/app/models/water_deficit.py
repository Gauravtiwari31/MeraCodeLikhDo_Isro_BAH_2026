"""
Water Deficit Estimation & Irrigation Advisory Engine
======================================================
USP 4.3 + 4.5: Confidence-Aware Advisory + Canal Command Optimizer

Implements the FAO-56 dual crop-coefficient method to estimate 8-day
crop water demand (ETc) and compute the deficit between ETc and the
sum of effective rainfall + actual ET.

Deficit thresholds drive categorical advisory classes, each carrying a
confidence flag from the uncertainty quantification module.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FAO-56 Crop Coefficients (Kc) by crop type and growth stage
# ---------------------------------------------------------------------------
# Source: FAO Irrigation and Drainage Paper No. 56 (Allen et al., 1998)

FAO56_KC: Dict[str, Dict[str, float]] = {
    "paddy_rice":   {"sowing_emergence": 1.05, "vegetative": 1.20, "flowering_heading": 1.20, "maturity_harvest": 0.90},
    "wheat":        {"sowing_emergence": 0.40, "vegetative": 1.15, "flowering_heading": 1.15, "maturity_harvest": 0.35},
    "maize":        {"sowing_emergence": 0.40, "vegetative": 1.20, "flowering_heading": 1.20, "maturity_harvest": 0.50},
    "cotton":       {"sowing_emergence": 0.45, "vegetative": 1.15, "flowering_heading": 1.20, "maturity_harvest": 0.70},
    "sugarcane":    {"sowing_emergence": 0.40, "vegetative": 1.25, "flowering_heading": 1.25, "maturity_harvest": 0.75},
    "groundnut":    {"sowing_emergence": 0.45, "vegetative": 1.05, "flowering_heading": 1.05, "maturity_harvest": 0.60},
    "vegetables":   {"sowing_emergence": 0.70, "vegetative": 1.05, "flowering_heading": 1.05, "maturity_harvest": 0.90},
    "non_crop":     {"sowing_emergence": 0.10, "vegetative": 0.10, "flowering_heading": 0.10, "maturity_harvest": 0.10},
    "fallow":       {"sowing_emergence": 0.15, "vegetative": 0.15, "flowering_heading": 0.15, "maturity_harvest": 0.15},
}

DEFAULT_KC = {"sowing_emergence": 0.50, "vegetative": 1.10, "flowering_heading": 1.10, "maturity_harvest": 0.60}

# Advisory categories
ADVISORY_CLASSES = {
    0: "no_action",
    1: "monitor",
    2: "irrigate_soon",
    3: "irrigate_now",
}

ADVISORY_PALETTE = {
    0: "#22C55E",   # green
    1: "#FDE047",   # yellow
    2: "#F97316",   # orange
    3: "#EF4444",   # red
}

ADVISORY_DESCRIPTIONS = {
    0: "Soil moisture adequate. No irrigation required.",
    1: "Watch soil moisture closely. Irrigate if stress develops.",
    2: "Deficit approaching critical level. Plan irrigation within 2–3 days.",
    3: "Critical water deficit. Irrigate immediately to prevent yield loss.",
}


# ---------------------------------------------------------------------------
# FAO-56 ETc computation
# ---------------------------------------------------------------------------

CROP_LABEL_MAP = {
    0: "non_crop", 1: "paddy_rice", 2: "wheat", 3: "sugarcane",
    4: "cotton",   5: "maize",      6: "groundnut", 7: "vegetables", 8: "fallow",
}

STAGE_LABEL_MAP = {
    0: "sowing_emergence", 1: "sowing_emergence", 2: "vegetative",
    3: "flowering_heading", 4: "maturity_harvest",
}


def compute_etc(
    et0: np.ndarray,             # (H, W) — reference ET (mm/day) e.g. from ERA5/CHIRPS
    crop_map: np.ndarray,        # (H, W) — integer crop class ID
    stage_map: np.ndarray,       # (H, W) — integer growth stage ID
    period_days: int = 8,
) -> np.ndarray:
    """
    FAO-56 Crop Water Demand (ETc) for an 8-day period.
    ETc = Kc × ET0 × period_days  [mm/8-day]

    Returns
    -------
    etc : (H, W) float — crop water demand in mm over the period
    """
    H, W = et0.shape
    kc_map = np.ones((H, W), dtype=np.float32) * 1.0

    for crop_id, crop_name in CROP_LABEL_MAP.items():
        crop_mask = crop_map == crop_id
        kc_table = FAO56_KC.get(crop_name, DEFAULT_KC)
        for stage_id, stage_name in STAGE_LABEL_MAP.items():
            stage_mask = stage_map == stage_id
            pixel_mask = crop_mask & stage_mask
            if pixel_mask.any():
                kc_map[pixel_mask] = kc_table.get(stage_name, 1.0)

    etc = kc_map * et0 * period_days
    logger.info(
        "ETc computed: mean=%.2f mm/8-day, min=%.2f, max=%.2f",
        etc.mean(), etc.min(), etc.max(),
    )
    return etc


def compute_water_deficit(
    etc: np.ndarray,                 # (H, W) — crop water demand (mm/period)
    effective_rainfall: np.ndarray,  # (H, W) — effective rainfall (mm/period)
    actual_et: np.ndarray,           # (H, W) — actual ET from remote sensing (mm/period)
) -> np.ndarray:
    """
    8-day water deficit.
    Deficit = ETc - (effective_rainfall + actual_ET)
    Positive deficit → irrigation needed; negative → surplus.

    Returns
    -------
    deficit : (H, W) float — water deficit in mm
    """
    deficit = etc - (effective_rainfall + actual_et)
    return deficit


# ---------------------------------------------------------------------------
# Irrigation advisory engine
# ---------------------------------------------------------------------------

# Deficit thresholds (mm/8-day) for advisory classes
# These are stage-sensitive; we use conservative defaults here
DEFICIT_THRESHOLDS = {
    "vegetative":        {"monitor": 10, "irrigate_soon": 25, "irrigate_now": 40},
    "flowering_heading": {"monitor":  8, "irrigate_soon": 18, "irrigate_now": 30},
    "sowing_emergence":  {"monitor": 12, "irrigate_soon": 28, "irrigate_now": 45},
    "maturity_harvest":  {"monitor": 15, "irrigate_soon": 35, "irrigate_now": 55},
    "pre_sowing":        {"monitor": 20, "irrigate_soon": 40, "irrigate_now": 60},
}

STAGE_DEFICIT_MAP = {
    0: "pre_sowing", 1: "sowing_emergence", 2: "vegetative",
    3: "flowering_heading", 4: "maturity_harvest",
}


def generate_advisory_map(
    deficit: np.ndarray,
    stage_map: np.ndarray,
    confidence_flag: np.ndarray,
) -> Dict[str, np.ndarray]:
    """
    USP 4.3: Generate irrigation advisory map with per-cell confidence flags.

    Parameters
    ----------
    deficit         : (H, W) float — water deficit in mm
    stage_map       : (H, W) int — growth stage per pixel
    confidence_flag : (H, W) int — 0=high, 1=medium, 2=low confidence

    Returns
    -------
    dict with:
        'advisory_map'     (H, W) int 0-3
        'confidence_flag'  (H, W) int 0-2
        'deficit_mm'       (H, W) float
    """
    H, W = deficit.shape
    advisory_map = np.zeros((H, W), dtype=np.uint8)

    for stage_id, stage_name in STAGE_DEFICIT_MAP.items():
        mask = stage_map == stage_id
        if not mask.any():
            continue

        thresholds = DEFICIT_THRESHOLDS.get(stage_name, DEFICIT_THRESHOLDS["vegetative"])
        d = deficit[mask]

        adv = np.zeros(d.shape, dtype=np.uint8)
        adv[d >= thresholds["monitor"]] = 1
        adv[d >= thresholds["irrigate_soon"]] = 2
        adv[d >= thresholds["irrigate_now"]] = 3
        advisory_map[mask] = adv

    logger.info(
        "Advisory map: no_action=%d, monitor=%d, irrigate_soon=%d, irrigate_now=%d",
        (advisory_map == 0).sum(), (advisory_map == 1).sum(),
        (advisory_map == 2).sum(), (advisory_map == 3).sum(),
    )

    return {
        "advisory_map": advisory_map,
        "confidence_flag": confidence_flag,
        "deficit_mm": deficit,
    }


# ---------------------------------------------------------------------------
# Canal Command Water-Budget Optimizer (USP 4.5)
# ---------------------------------------------------------------------------

def aggregate_to_canal_outlets(
    advisory_map: np.ndarray,
    deficit_mm: np.ndarray,
    outlet_boundaries: List[Dict[str, Any]],
    pixel_area_ha: float = 0.09,   # 30 m pixels → 0.09 ha
) -> List[Dict[str, Any]]:
    """
    USP 4.5: Canal Command Water-Budget Optimizer.

    Aggregates pixel-level water deficit up to canal outlet / command-area
    boundaries and suggests relative water-release prioritization across
    outlets — turning a monitoring map into an operational scheduling input
    for irrigation departments.

    Parameters
    ----------
    advisory_map        : (H, W) int — advisory class per pixel
    deficit_mm          : (H, W) float — water deficit per pixel (mm)
    outlet_boundaries   : list of dicts, each with 'outlet_id', 'name',
                          'pixel_mask' (boolean H×W array) or 'row_slice'/'col_slice'
    pixel_area_ha       : area per pixel in hectares

    Returns
    -------
    list of outlet records sorted by priority (highest deficit first)
    """
    outlet_results = []

    for outlet in outlet_boundaries:
        mask = outlet.get("pixel_mask")
        if mask is None:
            # Fallback: use row/col slices
            rs, re = outlet.get("row_slice", (0, advisory_map.shape[0]))
            cs, ce = outlet.get("col_slice", (0, advisory_map.shape[1]))
            mask = np.zeros(advisory_map.shape, dtype=bool)
            mask[rs:re, cs:ce] = True

        n_pixels = mask.sum()
        if n_pixels == 0:
            continue

        total_ha = n_pixels * pixel_area_ha
        total_deficit_mm = deficit_mm[mask].mean()
        total_volume_m3 = total_deficit_mm * 0.001 * total_ha * 10_000  # mm → m³

        irrigate_now_pct = float((advisory_map[mask] == 3).mean() * 100)
        irrigate_soon_pct = float((advisory_map[mask] == 2).mean() * 100)

        # Priority score: weighted sum of critical + urgent fractions
        priority_score = irrigate_now_pct * 1.0 + irrigate_soon_pct * 0.5

        outlet_results.append({
            "outlet_id":         outlet.get("outlet_id", "unknown"),
            "outlet_name":       outlet.get("name", outlet.get("outlet_id", "unknown")),
            "total_area_ha":     round(total_ha, 1),
            "mean_deficit_mm":   round(float(total_deficit_mm), 1),
            "total_volume_m3":   round(float(total_volume_m3), 0),
            "irrigate_now_pct":  round(irrigate_now_pct, 1),
            "irrigate_soon_pct": round(irrigate_soon_pct, 1),
            "priority_score":    round(priority_score, 1),
        })

    # Sort by priority (highest first)
    outlet_results.sort(key=lambda x: x["priority_score"], reverse=True)

    # Add rank
    for rank, outlet in enumerate(outlet_results, start=1):
        outlet["priority_rank"] = rank

    logger.info(
        "Canal optimizer: ranked %d outlets. Top priority: %s (score=%.1f)",
        len(outlet_results),
        outlet_results[0]["outlet_name"] if outlet_results else "none",
        outlet_results[0]["priority_score"] if outlet_results else 0,
    )

    return outlet_results
