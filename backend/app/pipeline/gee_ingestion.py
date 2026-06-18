"""
GEE Data Ingestion Pipeline
===========================
Pulls optical (Sentinel-2 L2A, Landsat-8/9, MODIS) and microwave SAR
(Sentinel-1 GRD, EOS-04) tiles from Google Earth Engine for a given AOI
and date range.

Architecture note: The SAR ingestion module is built as a swappable adapter
so that NISAR data streams can be plugged in with minimal rework (USP 4.6).
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy GEE import — fall back gracefully if not authenticated
# ---------------------------------------------------------------------------
try:
    import ee  # type: ignore
    _GEE_AVAILABLE = True
except ImportError:
    _GEE_AVAILABLE = False
    logger.warning("earthengine-api not installed; running in demo-data mode.")


# ---------------------------------------------------------------------------
# AOI helpers
# ---------------------------------------------------------------------------

def load_aoi(aoi_path: str | Path) -> Dict[str, Any]:
    """Load an AOI from a GeoJSON file and return as a dict."""
    with open(aoi_path, "r") as f:
        return json.load(f)


def aoi_to_ee_geometry(aoi_geojson: Dict[str, Any]):
    """Convert a GeoJSON feature/geometry to an ee.Geometry."""
    if not _GEE_AVAILABLE:
        raise RuntimeError("Google Earth Engine SDK not available.")
    geom = aoi_geojson.get("geometry", aoi_geojson)
    return ee.Geometry(geom)


# ---------------------------------------------------------------------------
# Optical data ingestion
# ---------------------------------------------------------------------------

def get_sentinel2_collection(
    aoi_geometry,
    start_date: str,
    end_date: str,
    cloud_threshold: float = 20.0,
) -> Any:
    """
    Fetch Sentinel-2 L2A surface reflectance, filtered by cloud cover.

    Returns an ee.ImageCollection with bands: B2, B3, B4, B8, B11, B12
    plus the computed indices: NDVI, EVI, NDWI.
    """
    if not _GEE_AVAILABLE:
        return None

    def add_indices(image):
        ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
        evi = image.expression(
            "2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))",
            {"NIR": image.select("B8"), "RED": image.select("B4"), "BLUE": image.select("B2")},
        ).rename("EVI")
        ndwi = image.normalizedDifference(["B3", "B8"]).rename("NDWI")
        return image.addBands([ndvi, evi, ndwi])

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi_geometry)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_threshold))
        .select(["B2", "B3", "B4", "B8", "B11", "B12"])
        .map(add_indices)
    )
    logger.info(
        "Sentinel-2 collection size: %d images (%s → %s)",
        collection.size().getInfo(),
        start_date,
        end_date,
    )
    return collection


def get_landsat_collection(
    aoi_geometry,
    start_date: str,
    end_date: str,
    cloud_threshold: float = 20.0,
) -> Any:
    """Fetch Landsat-8/9 OLI-2 surface reflectance with cloud masking."""
    if not _GEE_AVAILABLE:
        return None

    def mask_clouds(image):
        qa = image.select("QA_PIXEL")
        dilated = 1 << 1
        cloud = 1 << 3
        shadow = 1 << 4
        mask = qa.bitwiseAnd(dilated).eq(0).And(
            qa.bitwiseAnd(cloud).eq(0)
        ).And(qa.bitwiseAnd(shadow).eq(0))
        return image.updateMask(mask).multiply(0.0000275).add(-0.2)

    def add_indices(image):
        ndvi = image.normalizedDifference(["SR_B5", "SR_B4"]).rename("NDVI")
        ndwi = image.normalizedDifference(["SR_B3", "SR_B5"]).rename("NDWI")
        return image.addBands([ndvi, ndwi])

    collection = (
        ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        .merge(ee.ImageCollection("LANDSAT/LC08/C02/T1_L2"))
        .filterBounds(aoi_geometry)
        .filterDate(start_date, end_date)
        .map(mask_clouds)
        .map(add_indices)
    )
    return collection


def get_modis_ndvi(aoi_geometry, start_date: str, end_date: str) -> Any:
    """Fetch MODIS MOD13Q1 16-day NDVI/EVI composites (250 m)."""
    if not _GEE_AVAILABLE:
        return None
    return (
        ee.ImageCollection("MODIS/006/MOD13Q1")
        .filterBounds(aoi_geometry)
        .filterDate(start_date, end_date)
        .select(["NDVI", "EVI"])
        .map(lambda img: img.multiply(0.0001))  # scale factor
    )


# ---------------------------------------------------------------------------
# SAR (Sentinel-1 / EOS-04 adapter) — USP 4.6: NISAR-ready swappable adapter
# ---------------------------------------------------------------------------

class SARAdapter:
    """
    Swappable SAR ingestion adapter.

    Supports:
    - 'sentinel1' : Sentinel-1 GRD (VV/VH), free via GEE
    - 'eos04'     : ISRO EOS-04 SAR (C-band), via Bhoonidhi
    - 'nisar'     : NISAR (L/S band), planned — ready for integration

    Switch the `sensor` parameter to change data source with zero pipeline
    changes downstream (USP 4.6 — NISAR-ready, future-proof SAR ingestion).
    """

    SUPPORTED_SENSORS = ("sentinel1", "eos04", "nisar")

    def __init__(self, sensor: str = "sentinel1"):
        if sensor not in self.SUPPORTED_SENSORS:
            raise ValueError(f"Unsupported SAR sensor: {sensor}. Choose from {self.SUPPORTED_SENSORS}")
        self.sensor = sensor
        logger.info("SAR adapter initialized for sensor: %s", sensor)

    def get_collection(
        self,
        aoi_geometry,
        start_date: str,
        end_date: str,
        orbit_pass: str = "DESCENDING",
    ) -> Any:
        """Return a VV/VH backscatter collection for the configured sensor."""
        if self.sensor == "sentinel1":
            return self._get_sentinel1(aoi_geometry, start_date, end_date, orbit_pass)
        elif self.sensor == "eos04":
            return self._get_eos04_stub(aoi_geometry, start_date, end_date)
        elif self.sensor == "nisar":
            return self._get_nisar_stub(aoi_geometry, start_date, end_date)

    def _get_sentinel1(self, aoi_geometry, start_date, end_date, orbit_pass):
        if not _GEE_AVAILABLE:
            return None

        def add_ratio(image):
            ratio = image.select("VH").subtract(image.select("VV")).rename("VH_VV_ratio")
            return image.addBands(ratio)

        collection = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(aoi_geometry)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.eq("orbitProperties_pass", orbit_pass))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
            .select(["VV", "VH"])
            .map(add_ratio)
        )
        return collection

    def _get_eos04_stub(self, aoi_geometry, start_date, end_date):
        """
        EOS-04 ingestion stub.
        In production: call Bhoonidhi API, download GRD products,
        apply orbit correction and radiometric calibration, then return
        a harmonised VV/VH xarray Dataset matching the Sentinel-1 schema.
        """
        logger.info(
            "[EOS-04 stub] Would fetch ISRO EOS-04 SAR for %s → %s via Bhoonidhi.",
            start_date, end_date,
        )
        return None  # Replace with actual Bhoonidhi API call

    def _get_nisar_stub(self, aoi_geometry, start_date, end_date):
        """
        NISAR ingestion stub (USP 4.6).
        NISAR (L-band + S-band) data will stream via ASF DAAC / AWS S3.
        Once available, replace this stub with:
          - Download NISAR GCOV/SLC products
          - Convert L/S-band sigma0 to VV/VH-equivalent backscatter
          - Return harmonised Dataset matching Sentinel-1 schema
        No changes to downstream stress detection or advisory modules required.
        """
        logger.info("[NISAR stub] NISAR data not yet publicly available. Adapter ready.")
        return None


# ---------------------------------------------------------------------------
# 8-day temporal compositing
# ---------------------------------------------------------------------------

def make_8day_composites(
    collection,
    aoi_geometry,
    start_date: str,
    end_date: str,
    reducer=None,
) -> List[Dict[str, Any]]:
    """
    Build 8-day median composites from an ee.ImageCollection.

    Returns a list of (date_str, ee.Image) pairs.
    """
    if not _GEE_AVAILABLE or collection is None:
        return []

    if reducer is None:
        reducer = ee.Reducer.median()

    composites = []
    current = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    while current < end:
        period_end = min(current + timedelta(days=8), end)
        composite = (
            collection
            .filterDate(current.isoformat(), period_end.isoformat())
            .reduce(reducer)
            .clip(aoi_geometry)
        )
        composites.append({
            "date": current.isoformat(),
            "period_end": period_end.isoformat(),
            "image": composite,
        })
        current += timedelta(days=8)

    logger.info("Created %d 8-day composites from %s to %s", len(composites), start_date, end_date)
    return composites
