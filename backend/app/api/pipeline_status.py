"""Pipeline status and NDVI time series endpoint."""

from __future__ import annotations
import json, logging
from pathlib import Path
from fastapi import APIRouter, Query

from app.data.demo_generator import (
    generate_ndvi_timeseries, COMPOSITE_DATES, CANAL_OUTLETS
)

router = APIRouter()
logger = logging.getLogger(__name__)

DEMO_DATA_DIR = Path(__file__).parent.parent / "data" / "generated"


@router.get("/status", summary="Pipeline status and metadata")
async def get_pipeline_status():
    """Returns pipeline status, AOI metadata, and available date range."""
    return {
        "status": "operational",
        "mode": "demo",
        "aoi": {
            "name": "Bhakra_Canal_Command_Punjab",
            "bbox": {"min_lat": 30.0, "max_lat": 31.5, "min_lon": 75.5, "max_lon": 77.0},
            "area_ha": 87500,
            "canal_outlets": len(CANAL_OUTLETS),
        },
        "data_sources": {
            "optical": ["Sentinel-2 L2A", "Landsat-8/9", "MODIS MOD13Q1"],
            "sar": ["Sentinel-1 GRD (VV/VH)", "EOS-04 (adapter ready)", "NISAR (stub ready)"],
            "ancillary": ["IMD rainfall", "ERA5 ET", "FAO-56 Kc tables"],
        },
        "pipeline_stages": [
            "Data Ingestion (GEE / Bhoonidhi)",
            "Pre-processing (cloud mask, speckle filter, compositing)",
            "Feature Engineering (NDVI, EVI, NDWI, VCI, SAR, GLCM)",
            "Crop Classification (Foundation Embeddings + XGBoost)",
            "Phenology-Aware Stress Detection (SAR+Optical Fusion, MC Dropout)",
            "Water Deficit & Advisory (FAO-56 ETc, Canal Optimizer)",
            "Dashboard & Multilingual Delivery",
        ],
        "dates": COMPOSITE_DATES,
        "current_season": "kharif_2025",
        "last_update": COMPOSITE_DATES[-1],
        "usps_implemented": 8,
    }


@router.get("/ndvi-timeseries", summary="NDVI time series for a pixel")
async def get_ndvi_timeseries(
    row: int = Query(15, ge=0, le=29),
    col: int = Query(15, ge=0, le=29),
):
    """Returns NDVI + historical baseline time series for the selected pixel."""
    cached = DEMO_DATA_DIR / "ndvi_timeseries.json"
    if cached.exists():
        with open(cached) as f:
            data = json.load(f)
            for ts in data:
                if ts["pixel"]["row"] == row and ts["pixel"]["col"] == col:
                    return ts
    return generate_ndvi_timeseries(row=row, col=col)
