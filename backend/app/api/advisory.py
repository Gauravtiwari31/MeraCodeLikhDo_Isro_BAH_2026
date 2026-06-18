"""API endpoints for irrigation advisory maps and canal command optimizer."""

from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.data.demo_generator import (
    generate_advisory_map,
    generate_canal_outlet_priorities,
    COMPOSITE_DATES,
)

router = APIRouter()
logger = logging.getLogger(__name__)

DEMO_DATA_DIR = Path(__file__).parent.parent / "data" / "generated"


from app.core.config import settings

def _get_advisory_map(date_str: str) -> Dict[str, Any]:
    if not settings.USE_DEMO_DATA:
        from app.pipeline.runner import run_live_pipeline
        return run_live_pipeline(date_str)
        
    cached = DEMO_DATA_DIR / f"advisory_{date_str}.json"
    if cached.exists():
        with open(cached) as f:
            return json.load(f)
    return generate_advisory_map(date_str)


def _get_canal_priorities(date_str: str) -> List[Dict[str, Any]]:
    cached = DEMO_DATA_DIR / "canal_outlets.json"
    if cached.exists():
        with open(cached) as f:
            data = json.load(f)
            return data.get(date_str, generate_canal_outlet_priorities(date_str))
    return generate_canal_outlet_priorities(date_str)


@router.get("/map", summary="Get irrigation advisory map for a given date")
async def get_advisory_map(
    date: str = Query(COMPOSITE_DATES[-1], description="8-day composite date (YYYY-MM-DD)"),
):
    """
    Returns confidence-aware irrigation advisory GeoJSON.

    USP 4.3: Each cell has advisory_class (0–3) + confidence_flag:
      0 = No Action  | 1 = Monitor | 2 = Irrigate Soon | 3 = Irrigate Now

    USP 4.7: PMFBY-grade auditability — each feature carries a
    timestamped record_id for insurance claim verification.
    """
    if date not in COMPOSITE_DATES:
        raise HTTPException(status_code=400, detail=f"Invalid date: {date}")
    return _get_advisory_map(date)


@router.get("/canal-outlets", summary="Canal outlet water-release prioritization")
async def get_canal_outlet_priorities(
    date: str = Query(COMPOSITE_DATES[-1], description="8-day composite date"),
):
    """
    USP 4.5: Canal Command Water-Budget Optimizer.

    Aggregates pixel-level water deficit to canal outlet level and returns
    a ranked list of outlets sorted by irrigation urgency (priority_score).
    Turns a monitoring map into an operational scheduling input for
    irrigation departments.
    """
    if date not in COMPOSITE_DATES:
        raise HTTPException(status_code=400, detail=f"Invalid date: {date}")
    outlets = _get_canal_priorities(date)
    return {
        "date": date,
        "aoi": "Bhakra_Canal_Command_Punjab",
        "outlets": outlets,
        "total_outlets": len(outlets),
        "method": "FAO-56 ETc aggregation + Deficit-weighted priority ranking",
    }


@router.get("/summary", summary="Advisory distribution statistics")
async def get_advisory_summary(
    date: str = Query(COMPOSITE_DATES[-1]),
):
    """Returns distribution of advisory classes for a given date."""
    data = _get_advisory_map(date)
    from collections import Counter
    counts = Counter(f["properties"]["advisory_label"] for f in data["features"])
    total = len(data["features"])
    mean_deficit = sum(
        f["properties"]["deficit_mm"] for f in data["features"]
    ) / total if total else 0
    return {
        "date": date,
        "distribution_pct": {k: round(v / total * 100, 1) for k, v in counts.items()},
        "mean_deficit_mm": round(mean_deficit, 1),
        "irrigate_now_pct": data["metadata"]["irrigate_now_pct"],
    }
