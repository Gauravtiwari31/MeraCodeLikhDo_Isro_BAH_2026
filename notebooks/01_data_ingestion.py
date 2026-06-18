"""
Jupyter Notebook: 01 — Data Ingestion
=====================================
Demonstrates pulling optical (Sentinel-2, Landsat) and SAR (Sentinel-1)
data from Google Earth Engine for the pilot command area (Bhakra Canal,
Punjab) using the MeraCodeLikhDo pipeline.

Run in Google Colab for free GEE compute + no local setup required.
"""

# %% [markdown]
# # 📡 Step 1: Data Ingestion — Optical & SAR Satellite Data
# 
# **MeraCodeLikhDo | ISRO BAH 2026**
# 
# This notebook demonstrates the data ingestion step of the pipeline.
# We pull:
# - 🌿 **Sentinel-2 L2A** (10 m optical, cloud-filtered)
# - 🛰️ **Sentinel-1 GRD** (10 m SAR, VV/VH polarization)
# - 📊 **MODIS MOD13Q1** (250 m, 16-day NDVI composites)
# 
# for the **Bhakra Canal Command, Punjab** pilot area over the Kharif 2025 season.

# %% Cell 1: Install dependencies (Colab)
# !pip install earthengine-api rasterio geopandas xarray rioxarray numpy matplotlib -q

# %% Cell 2: Authenticate with Google Earth Engine
import ee

# Uncomment for interactive auth:
# ee.Authenticate()
# ee.Initialize(project='your-gee-project-id')

print("GEE SDK version:", ee.__version__ if hasattr(ee, '__version__') else "not authenticated")
print("Note: Run ee.Authenticate() and ee.Initialize() with your GCP project to enable live data.")

# %% Cell 3: Define pilot AOI — Bhakra Canal Command, Punjab
AOI_COORDS = [
    [75.5, 30.0], [77.0, 30.0],
    [77.0, 31.5], [75.5, 31.5],
    [75.5, 30.0],
]

KHARIF_START = "2025-06-01"
KHARIF_END   = "2025-11-01"

print(f"AOI: Bhakra Canal Command, Punjab")
print(f"Bbox: 30.0°N–31.5°N, 75.5°E–77.0°E")
print(f"Season: Kharif {KHARIF_START} → {KHARIF_END}")

# %% Cell 4: GEE — Sentinel-2 collection
"""
# Uncomment when GEE is authenticated

geometry = ee.Geometry.Polygon([AOI_COORDS])

def add_indices(image):
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    evi = image.expression(
        '2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))',
        {'NIR': image.select('B8'), 'RED': image.select('B4'), 'BLUE': image.select('B2')}
    ).rename('EVI')
    ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI')
    return image.addBands([ndvi, evi, ndwi])

s2_collection = (
    ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(geometry)
    .filterDate(KHARIF_START, KHARIF_END)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    .select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12'])
    .map(add_indices)
)

print(f"Sentinel-2 collection size: {s2_collection.size().getInfo()} images")
"""
print("Live GEE disabled — using demo data. See backend/app/pipeline/gee_ingestion.py for full code.")

# %% Cell 5: GEE — Sentinel-1 SAR collection  
"""
# Uncomment when GEE is authenticated

def add_sar_ratio(image):
    ratio = image.select('VH').subtract(image.select('VV')).rename('VH_VV_ratio')
    return image.addBands(ratio)

s1_collection = (
    ee.ImageCollection('COPERNICUS/S1_GRD')
    .filterBounds(geometry)
    .filterDate(KHARIF_START, KHARIF_END)
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
    .select(['VV', 'VH'])
    .map(add_sar_ratio)
)

print(f"Sentinel-1 collection size: {s1_collection.size().getInfo()} images")
"""
print("See backend/app/pipeline/gee_ingestion.py -> SARAdapter for full SAR ingestion code.")

# %% Cell 6: Demo — Simulate NDVI time series
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

dates = [
    "2025-06-01", "2025-06-09", "2025-06-17", "2025-06-25",
    "2025-07-03", "2025-07-11", "2025-07-19", "2025-07-27",
    "2025-08-04", "2025-08-12", "2025-08-20", "2025-08-28",
    "2025-09-05", "2025-09-13", "2025-09-21", "2025-09-29",
    "2025-10-07", "2025-10-15", "2025-10-23", "2025-10-31",
]

t = np.linspace(0, 1, len(dates))
ndvi_paddy = 0.25 + 0.60 * np.exp(-((t - 0.55) ** 2) / (2 * 0.06)) + np.random.normal(0, 0.015, len(dates))
ndvi_wheat = 0.20 + 0.55 * np.exp(-((t - 0.45) ** 2) / (2 * 0.07)) + np.random.normal(0, 0.015, len(dates))

plt.figure(figsize=(12, 5))
plt.plot(dates, ndvi_paddy, 'g-o', label='Paddy Rice', linewidth=2, markersize=5)
plt.plot(dates, ndvi_wheat, 'b-s', label='Wheat',      linewidth=2, markersize=5)
plt.axhline(y=0.25, color='orange', linestyle='--', label='SOS threshold (0.25)')
plt.xlabel('Date (8-day composites)')
plt.ylabel('NDVI')
plt.title('Kharif 2025 — Multi-temporal NDVI Profile\nBhakra Canal Command, Punjab (Simulated)')
plt.xticks(dates[::4], rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig('01_ndvi_timeseries.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: 01_ndvi_timeseries.png")

# %% Cell 7: SAR VV/VH time series (simulated)
vv = -12.0 + 3.0 * np.sin(t * np.pi) + np.random.normal(0, 0.5, len(dates))
vh = -18.0 + 4.0 * np.sin(t * np.pi) + np.random.normal(0, 0.6, len(dates))
vh_vv_ratio = vh - vv   # in dB

plt.figure(figsize=(12, 5))
plt.plot(dates, vv, 'b-o', label='VV backscatter (dB)', linewidth=2, markersize=5)
plt.plot(dates, vh, 'r-s', label='VH backscatter (dB)', linewidth=2, markersize=5)
plt.plot(dates, vh_vv_ratio, 'g--^', label='VH/VV ratio (dB)', linewidth=1.5, markersize=4)
plt.xlabel('Date')
plt.ylabel('Backscatter (dB)')
plt.title('Kharif 2025 — Sentinel-1 SAR Backscatter Profile (Simulated)')
plt.xticks(dates[::4], rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig('01_sar_timeseries.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: 01_sar_timeseries.png")
print("\nData ingestion notebook complete.")
