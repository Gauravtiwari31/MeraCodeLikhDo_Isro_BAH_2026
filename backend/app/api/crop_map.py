"""API endpoints for crop type classification map."""

from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from app.data.demo_generator import generate_crop_map, COMPOSITE_DATES

router = APIRouter()
logger = logging.getLogger(__name__)

DEMO_DATA_DIR = Path(__file__).parent.parent / "data" / "generated"


def _load_or_generate_crop_map() -> Dict[str, Any]:
    cached = DEMO_DATA_DIR / "crop_map.json"
    if cached.exists():
        with open(cached) as f:
            return json.load(f)
    return generate_crop_map()


@router.get("/", summary="Get crop type classification map")
async def get_crop_map(
    season: str = Query("kharif_2025", description="Crop season identifier"),
    aoi: str = Query("Bhakra_Canal_Command_Punjab", description="Area of interest"),
):
    """
    Returns a GeoJSON FeatureCollection of crop-type classification for the
    pilot command area. Each feature is a 30×30 grid cell with:
    - crop_id, crop_name, color
    - classifier confidence
    - methodology and data source

    USP 4.1: Foundation-Model Embeddings + XGBoost (Prithvi-EO-2.0 / Clay)
    """
    try:
        data = _load_or_generate_crop_map()
        data["metadata"]["season"] = season
        data["metadata"]["aoi"] = aoi
        return data
    except Exception as e:
        logger.error("Error generating crop map: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", summary="Crop area statistics")
async def get_crop_summary(
    season: str = Query("kharif_2025"),
):
    """Returns area statistics (ha) per crop type for the pilot command area."""
    data = _load_or_generate_crop_map()
    from collections import Counter
    counts = Counter(f["properties"]["crop_name"] for f in data["features"])
    pixel_area_ha = 0.09  # 30 m resolution
    return {
        "season": season,
        "area_by_crop_ha": {
            crop: round(count * pixel_area_ha, 1)
            for crop, count in sorted(counts.items(), key=lambda x: -x[1])
        },
        "total_pixels": len(data["features"]),
        "model_accuracy": data["metadata"]["overall_accuracy"],
        "kappa": data["metadata"]["kappa_coefficient"],
    }


@router.get("/dates", summary="Available composite dates")
async def get_available_dates():
    return {"dates": COMPOSITE_DATES, "total": len(COMPOSITE_DATES)}
