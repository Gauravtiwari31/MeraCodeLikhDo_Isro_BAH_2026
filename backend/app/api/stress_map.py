"""API endpoints for phenology-aware moisture stress maps."""

from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from app.data.demo_generator import generate_stress_map, COMPOSITE_DATES

router = APIRouter()
logger = logging.getLogger(__name__)

DEMO_DATA_DIR = Path(__file__).parent.parent / "data" / "generated"


def _get_stress_map(date_str: str) -> Dict[str, Any]:
    cached = DEMO_DATA_DIR / f"stress_{date_str}.json"
    if cached.exists():
        with open(cached) as f:
            return json.load(f)
    return generate_stress_map(date_str)


@router.get("/", summary="Get stress map for a given date")
async def get_stress_map(
    date: str = Query(COMPOSITE_DATES[-1], description="8-day composite date (YYYY-MM-DD)"),
):
    """
    Returns phenology-aware moisture stress GeoJSON for one 8-day composite.

    USP 4.2: True Stage-Level SAR+Optical Fusion — each pixel has:
    - stress_class (0–3), stress_label
    - growth_stage (sowing_emergence / vegetative / flowering_heading / maturity_harvest)
    - uncertainty + confidence_flag (MC Dropout — USP 4.3)

    USP 4.3: Every cell ships with a confidence flag so operators know
    when to trust the model vs. verify in the field.
    """
    if date not in COMPOSITE_DATES:
        raise HTTPException(
            status_code=400,
            detail=f"Date {date} not available. Use /api/v1/crop-map/dates for valid dates.",
        )
    return _get_stress_map(date)


@router.get("/time-series/{row}/{col}", summary="Stress time-series for a pixel")
async def get_pixel_stress_timeseries(row: int, col: int):
    """Returns stress class and index for all 8-day composites at a given pixel."""
    results = []
    for date_str in COMPOSITE_DATES:
        data = _get_stress_map(date_str)
        features = [
            f for f in data["features"]
            if f["properties"]["row"] == row and f["properties"]["col"] == col
        ]
        if features:
            props = features[0]["properties"]
            results.append({
                "date": date_str,
                "stress_class": props["stress_class"],
                "stress_label": props["stress_label"],
                "stress_index": props["stress_index"],
                "growth_stage": props["growth_stage"],
                "confidence_label": props["confidence_label"],
            })
    return {"pixel": {"row": row, "col": col}, "timeseries": results}


@router.get("/summary", summary="Stressed area statistics")
async def get_stress_summary(
    date: str = Query(COMPOSITE_DATES[-1]),
):
    """Returns percentage of area in each stress class for a given date."""
    data = _get_stress_map(date)
    from collections import Counter
    counts = Counter(f["properties"]["stress_label"] for f in data["features"])
    total = len(data["features"])
    return {
        "date": date,
        "distribution_pct": {k: round(v / total * 100, 1) for k, v in counts.items()},
        "total_pixels": total,
        "stressed_area_pct": data["metadata"]["stressed_pixels_pct"],
    }
