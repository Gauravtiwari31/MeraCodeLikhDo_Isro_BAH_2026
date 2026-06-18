"""
Demo Data Generator
===================
Generates realistic pre-computed GeoJSON outputs for the pilot AOI
(Bhakra Canal Command, Punjab) to power the dashboard without requiring
live GEE authentication.

All outputs are labelled as "simulated" — the real pipeline code is in
pipeline/ and models/ and can be run with GEE credentials.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Pilot AOI: Bhakra Canal Command, Punjab
# Approximate bounding box: 30.0°N–31.5°N, 75.5°E–77.0°E
# ---------------------------------------------------------------------------
AOI_BBOX = {
    "min_lat": 30.0, "max_lat": 31.5,
    "min_lon": 75.5, "max_lon": 77.0,
}

GRID_ROWS = 30
GRID_COLS = 30

# ---------------------------------------------------------------------------
# 8-day composite dates for Kharif 2025 season
# ---------------------------------------------------------------------------
COMPOSITE_DATES = [
    "2025-06-01", "2025-06-09", "2025-06-17", "2025-06-25",
    "2025-07-03", "2025-07-11", "2025-07-19", "2025-07-27",
    "2025-08-04", "2025-08-12", "2025-08-20", "2025-08-28",
    "2025-09-05", "2025-09-13", "2025-09-21", "2025-09-29",
    "2025-10-07", "2025-10-15", "2025-10-23", "2025-10-31",
]

# Canal outlet definitions for the pilot command area
CANAL_OUTLETS = [
    {"outlet_id": "BO-01", "name": "Bhakra Outlet 1 — Ludhiana North"},
    {"outlet_id": "BO-02", "name": "Bhakra Outlet 2 — Fatehgarh Sahib"},
    {"outlet_id": "BO-03", "name": "Bhakra Outlet 3 — Patiala East"},
    {"outlet_id": "BO-04", "name": "Bhakra Outlet 4 — Sangrur West"},
    {"outlet_id": "BO-05", "name": "Bhakra Outlet 5 — Barnala"},
    {"outlet_id": "BO-06", "name": "Bhakra Outlet 6 — Ropar"},
]

CROP_NAMES = {
    0: "non_crop", 1: "paddy_rice", 2: "wheat", 3: "sugarcane",
    4: "cotton",   5: "maize",      6: "groundnut", 7: "vegetables", 8: "fallow",
}

CROP_PALETTE = {
    0: "#6B7280", 1: "#22C55E", 2: "#EAB308", 3: "#A78BFA",
    4: "#F97316", 5: "#84CC16", 6: "#FB923C", 7: "#34D399", 8: "#D1D5DB",
}

STRESS_PALETTE = {0: "#22C55E", 1: "#FDE047", 2: "#F97316", 3: "#EF4444"}
ADVISORY_PALETTE = {0: "#22C55E", 1: "#FDE047", 2: "#F97316", 3: "#EF4444"}

ADVISORY_LABELS = {
    0: "No Action", 1: "Monitor", 2: "Irrigate Soon", 3: "Irrigate Now"
}
STRESS_LABELS = {0: "No Stress", 1: "Mild", 2: "Moderate", 3: "Severe"}
CONFIDENCE_LABELS = {0: "HIGH", 1: "MEDIUM", 2: "LOW"}


def _pixel_to_coords(row: int, col: int) -> Tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) for a grid cell."""
    lat_step = (AOI_BBOX["max_lat"] - AOI_BBOX["min_lat"]) / GRID_ROWS
    lon_step = (AOI_BBOX["max_lon"] - AOI_BBOX["min_lon"]) / GRID_COLS
    min_lat = AOI_BBOX["min_lat"] + row * lat_step
    min_lon = AOI_BBOX["min_lon"] + col * lon_step
    return min_lon, min_lat, min_lon + lon_step, min_lat + lat_step


def _make_cell_polygon(min_lon, min_lat, max_lon, max_lat) -> Dict:
    return {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat], [max_lon, min_lat],
            [max_lon, max_lat], [min_lon, max_lat], [min_lon, min_lat],
        ]],
    }


def generate_crop_map(seed: int = 42) -> Dict[str, Any]:
    """Generate a realistic crop-type map for the pilot AOI."""
    rng = np.random.default_rng(seed)

    # Realistic distribution for Punjab Kharif: mostly paddy_rice (1) + cotton (4)
    class_probs = [0.05, 0.45, 0.03, 0.05, 0.15, 0.08, 0.05, 0.07, 0.07]
    class_ids = list(range(9))

    features = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            # Spatial smoothing: use neighbour bias
            base_class = rng.choice(class_ids, p=class_probs)
            # Override with paddy belt in north / cotton in south
            if row < GRID_ROWS // 2:
                base_class = rng.choice([1, 4, 7, 2], p=[0.55, 0.20, 0.15, 0.10])
            else:
                base_class = rng.choice([4, 1, 8, 6], p=[0.40, 0.30, 0.15, 0.15])

            confidence = rng.uniform(0.72, 0.99)
            min_lon, min_lat, max_lon, max_lat = _pixel_to_coords(row, col)

            features.append({
                "type": "Feature",
                "geometry": _make_cell_polygon(min_lon, min_lat, max_lon, max_lat),
                "properties": {
                    "row": row, "col": col,
                    "crop_id": int(base_class),
                    "crop_name": CROP_NAMES[base_class],
                    "color": CROP_PALETTE[base_class],
                    "confidence": round(float(confidence), 3),
                    "method": "Foundation-Model Embeddings + XGBoost",
                    "data_source": "Sentinel-2 L2A + Landsat-8 (simulated)",
                    "season": "kharif_2025",
                },
            })

    return {
        "type": "FeatureCollection",
        "metadata": {
            "layer": "crop_type_map",
            "season": "kharif_2025",
            "aoi": "Bhakra_Canal_Command_Punjab",
            "model": "Foundation-Model Embeddings + XGBoost",
            "overall_accuracy": 0.887,
            "kappa_coefficient": 0.863,
            "n_classes": 9,
            "simulated": True,
        },
        "features": features,
    }


def generate_stress_map(date_str: str, seed: int = 0) -> Dict[str, Any]:
    """Generate a phenology-aware stress map for one 8-day composite."""
    rng = np.random.default_rng(seed + hash(date_str) % 10000)

    # Determine approximate season progress (0=early, 1=peak, 2=late)
    date_idx = COMPOSITE_DATES.index(date_str) if date_str in COMPOSITE_DATES else 10
    season_progress = date_idx / len(COMPOSITE_DATES)

    # More stress in early and late season, less at peak
    stress_bias = abs(season_progress - 0.5) * 2

    stage_map_names = {0: "sowing_emergence", 1: "sowing_emergence", 2: "vegetative",
                       3: "flowering_heading", 4: "maturity_harvest"}

    features = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            # Assign growth stage based on row (north → earlier stage for demo)
            stage_id = min(4, int(season_progress * 5) + rng.integers(-1, 2))
            stage_id = max(0, stage_id)

            # Stress more likely in drier south-east regions
            spatial_stress = (row / GRID_ROWS) * 0.3 + (col / GRID_COLS) * 0.2
            stress_prob = np.clip(stress_bias * 0.5 + spatial_stress, 0, 1)

            if stress_prob > 0.4:
                raw_p = [
                    max(0.05, 1 - stress_prob - 0.3),
                    0.30,
                    0.25,
                    min(0.40, max(0.05, stress_prob - 0.2)),
                ]
            else:
                raw_p = [0.55, 0.25, 0.15, 0.05]
            total_p = sum(raw_p)
            norm_p = [v / total_p for v in raw_p]
            stress_class = int(rng.choice([0, 1, 2, 3], p=norm_p))

            stress_index = rng.uniform(
                [0.0, 0.15, 0.40, 0.65][stress_class],
                [0.15, 0.40, 0.65, 1.00][stress_class],
            )
            uncertainty = rng.uniform(0.01, 0.12)
            confidence_flag = 0 if uncertainty < 0.05 else (1 if uncertainty < 0.10 else 2)

            min_lon, min_lat, max_lon, max_lat = _pixel_to_coords(row, col)

            features.append({
                "type": "Feature",
                "geometry": _make_cell_polygon(min_lon, min_lat, max_lon, max_lat),
                "properties": {
                    "row": row, "col": col,
                    "date": date_str,
                    "stress_class": stress_class,
                    "stress_label": STRESS_LABELS[stress_class],
                    "stress_index": round(float(stress_index), 3),
                    "growth_stage_id": int(stage_id),
                    "growth_stage": stage_map_names.get(stage_id, "vegetative"),
                    "uncertainty": round(float(uncertainty), 3),
                    "confidence_flag": confidence_flag,
                    "confidence_label": CONFIDENCE_LABELS[confidence_flag],
                    "color": STRESS_PALETTE[stress_class],
                    "method": "Stage-Aware SAR+Optical Fusion + MC Dropout",
                    "simulated": True,
                },
            })

    stressed_count = sum(1 for f in features if f["properties"]["stress_class"] >= 2)

    return {
        "type": "FeatureCollection",
        "metadata": {
            "layer": "stress_map",
            "date": date_str,
            "season": "kharif_2025",
            "aoi": "Bhakra_Canal_Command_Punjab",
            "stressed_pixels_pct": round(stressed_count / len(features) * 100, 1),
            "simulated": True,
        },
        "features": features,
    }


def generate_advisory_map(date_str: str, seed: int = 1) -> Dict[str, Any]:
    """Generate an irrigation advisory map with confidence flags."""
    rng = np.random.default_rng(seed + hash(date_str) % 10000)
    date_idx = COMPOSITE_DATES.index(date_str) if date_str in COMPOSITE_DATES else 10
    season_progress = date_idx / len(COMPOSITE_DATES)
    stress_bias = abs(season_progress - 0.5) * 1.8

    features = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            spatial_factor = (row + col) / (GRID_ROWS + GRID_COLS)
            deficit_mm = rng.uniform(0, 60) * (0.3 + stress_bias * 0.7 + spatial_factor * 0.3)

            if deficit_mm < 10:
                advisory = 0
            elif deficit_mm < 25:
                advisory = 1
            elif deficit_mm < 40:
                advisory = 2
            else:
                advisory = 3

            confidence_flag = rng.choice([0, 1, 2], p=[0.55, 0.30, 0.15])
            min_lon, min_lat, max_lon, max_lat = _pixel_to_coords(row, col)

            # PMFBY auditability: timestamped record (USP 4.7)
            outlet_id = CANAL_OUTLETS[(row * GRID_COLS + col) // (GRID_ROWS * GRID_COLS // len(CANAL_OUTLETS))]["outlet_id"]

            features.append({
                "type": "Feature",
                "geometry": _make_cell_polygon(min_lon, min_lat, max_lon, max_lat),
                "properties": {
                    "row": row, "col": col,
                    "date": date_str,
                    "advisory_class": advisory,
                    "advisory_label": ADVISORY_LABELS[advisory],
                    "deficit_mm": round(float(deficit_mm), 1),
                    "confidence_flag": int(confidence_flag),
                    "confidence_label": CONFIDENCE_LABELS[int(confidence_flag)],
                    "color": ADVISORY_PALETTE[advisory],
                    "outlet_id": outlet_id,
                    "method": "FAO-56 ETc + Water Balance",
                    "record_id": f"MCLD-{date_str}-{row:03d}-{col:03d}",  # PMFBY audit trail
                    "simulated": True,
                },
            })

    return {
        "type": "FeatureCollection",
        "metadata": {
            "layer": "advisory_map",
            "date": date_str,
            "season": "kharif_2025",
            "aoi": "Bhakra_Canal_Command_Punjab",
            "irrigate_now_pct": round(sum(1 for f in features if f["properties"]["advisory_class"] == 3) / len(features) * 100, 1),
            "simulated": True,
        },
        "features": features,
    }


def generate_canal_outlet_priorities(date_str: str, seed: int = 2) -> List[Dict[str, Any]]:
    """Generate canal outlet priority ranking for the pilot command area."""
    rng = np.random.default_rng(seed + hash(date_str) % 10000)
    date_idx = COMPOSITE_DATES.index(date_str) if date_str in COMPOSITE_DATES else 10
    stress = abs(date_idx / len(COMPOSITE_DATES) - 0.5) * 2

    results = []
    for outlet in CANAL_OUTLETS:
        base_deficit = rng.uniform(5, 55) * (0.4 + stress * 0.6)
        irrigate_now_pct = min(100, max(0, float(rng.uniform(0, 60) * stress)))
        irrigate_soon_pct = min(100 - irrigate_now_pct, float(rng.uniform(10, 40)))
        priority = irrigate_now_pct + irrigate_soon_pct * 0.5

        results.append({
            "outlet_id": outlet["outlet_id"],
            "outlet_name": outlet["name"],
            "total_area_ha": round(float(rng.uniform(1200, 4500)), 0),
            "mean_deficit_mm": round(float(base_deficit), 1),
            "total_volume_m3": round(float(base_deficit * rng.uniform(800, 2500)), 0),
            "irrigate_now_pct": round(irrigate_now_pct, 1),
            "irrigate_soon_pct": round(irrigate_soon_pct, 1),
            "priority_score": round(priority, 1),
            "date": date_str,
        })

    results.sort(key=lambda x: x["priority_score"], reverse=True)
    for rank, r in enumerate(results, 1):
        r["priority_rank"] = rank

    return results


def generate_ndvi_timeseries(row: int = 15, col: int = 15, seed: int = 99) -> Dict[str, Any]:
    """Generate a realistic NDVI time series for a single pixel."""
    rng = np.random.default_rng(seed + row * 100 + col)
    n = len(COMPOSITE_DATES)

    # Bell-curve NDVI profile for Kharif (peak around mid-season)
    t = np.linspace(0, 1, n)
    ndvi = 0.25 + 0.55 * np.exp(-((t - 0.55) ** 2) / (2 * 0.05))
    ndvi += rng.normal(0, 0.015, n)
    ndvi = np.clip(ndvi, 0.05, 0.95).tolist()

    historical_mean = [v - rng.uniform(0.02, 0.08) for v in ndvi]
    historical_std = [rng.uniform(0.02, 0.06) for _ in ndvi]

    return {
        "pixel": {"row": row, "col": col},
        "dates": COMPOSITE_DATES,
        "ndvi": [round(v, 3) for v in ndvi],
        "ndvi_historical_mean": [round(v, 3) for v in historical_mean],
        "ndvi_historical_std": [round(v, 3) for v in historical_std],
        "crop_name": "paddy_rice",
        "season": "kharif_2025",
    }


def save_all_demo_data(output_dir: Path):
    """Pre-generate and save all demo data files to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating crop map...")
    crop_map = generate_crop_map()
    with open(output_dir / "crop_map.json", "w") as f:
        json.dump(crop_map, f, separators=(",", ":"))

    print("Generating stress maps...")
    for date_str in COMPOSITE_DATES:
        stress = generate_stress_map(date_str)
        fname = f"stress_{date_str}.json"
        with open(output_dir / fname, "w") as f:
            json.dump(stress, f, separators=(",", ":"))

    print("Generating advisory maps...")
    for date_str in COMPOSITE_DATES:
        adv = generate_advisory_map(date_str)
        fname = f"advisory_{date_str}.json"
        with open(output_dir / fname, "w") as f:
            json.dump(adv, f, separators=(",", ":"))

    print("Generating canal outlet priorities...")
    canal = {d: generate_canal_outlet_priorities(d) for d in COMPOSITE_DATES}
    with open(output_dir / "canal_outlets.json", "w") as f:
        json.dump(canal, f, separators=(",", ":"))

    print("Generating NDVI time series (sample pixels)...")
    ts_data = [generate_ndvi_timeseries(r, c) for r, c in [(15, 15), (5, 10), (25, 20)]]
    with open(output_dir / "ndvi_timeseries.json", "w") as f:
        json.dump(ts_data, f, separators=(",", ":"))

    print(f"✅ Demo data saved to {output_dir}")


if __name__ == "__main__":
    save_all_demo_data(Path(__file__).parent / "generated")
