"""
Notebook 02 — Feature Engineering
===================================
NDVI, EVI, NDWI, VCI, SAR texture (GLCM), phenometrics
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
matplotlib.use = lambda *a, **kw: None
import sys
sys.path.insert(0, '../backend')

# --- Load feature engineering module
from app.pipeline.feature_engineering import (
    compute_ndvi, compute_evi, compute_ndwi, compute_vci, compute_smi,
    compute_glcm_texture, compute_phenometrics, build_feature_cube,
    assign_growth_stage_per_pixel,
)

# --- Simulate a small 30×30 raster for demonstration
H, W, T = 30, 30, 20
rng = np.random.default_rng(42)

# Simulate multi-temporal reflectance bands
nir_stack  = rng.uniform(0.2, 0.6, (T, H, W))
red_stack  = rng.uniform(0.05, 0.2, (T, H, W))
green_stack= rng.uniform(0.05, 0.15, (T, H, W))
blue_stack = rng.uniform(0.02, 0.08, (T, H, W))
vv_stack   = rng.uniform(-20, -8, (T, H, W))
vh_stack   = rng.uniform(-28, -12, (T, H, W))

# Add seasonal NDVI signal (bell curve)
t_arr = np.linspace(0, 1, T)
for t in range(T):
    peak = 0.45 * np.exp(-((t_arr[t] - 0.55)**2) / (2 * 0.05))
    nir_stack[t] += peak
    red_stack[t]  -= peak * 0.3

ndvi_stack = compute_ndvi(nir_stack, red_stack)
evi_stack  = compute_evi(nir_stack, red_stack, blue_stack)
ndwi_stack = compute_ndwi(green_stack, nir_stack)

ndvi_hist_min = ndvi_stack.min(axis=0) - rng.uniform(0.02, 0.08, (H, W))
ndvi_hist_max = ndvi_stack.max(axis=0) + rng.uniform(0.02, 0.08, (H, W))

vci_stack = compute_vci(ndvi_stack[-1], ndvi_hist_min, ndvi_hist_max)
smi_stack = compute_smi(vv_stack[-1], vh_stack[-1])

# Phenometrics
dates = [
    "2025-06-01","2025-06-09","2025-06-17","2025-06-25",
    "2025-07-03","2025-07-11","2025-07-19","2025-07-27",
    "2025-08-04","2025-08-12","2025-08-20","2025-08-28",
    "2025-09-05","2025-09-13","2025-09-21","2025-09-29",
    "2025-10-07","2025-10-15","2025-10-23","2025-10-31",
]

pheno = compute_phenometrics(ndvi_stack, dates)
print("=== Phenological Metrics ===")
print(f"Start of Season: {pheno['sos_date']} (step {pheno['sos_index']})")
print(f"Peak NDVI:       {pheno['peak_date']} (step {pheno['peak_index']})")
print(f"LGP (8-day steps): {pheno['lgp']}")
print(f"Current Stage:   {pheno['current_stage']}")

stage_map = assign_growth_stage_per_pixel(ndvi_stack, current_t=T-1)
stage_names = {0:'pre_sowing',1:'sowing',2:'vegetative',3:'flowering',4:'maturity'}
print("\n=== Growth Stage Distribution ===")
for sid, sname in stage_names.items():
    count = (stage_map == sid).sum()
    print(f"  {sname}: {count} pixels ({count/stage_map.size*100:.1f}%)")

# Feature cube
feature_cube = build_feature_cube(
    ndvi_stack, evi_stack, ndwi_stack,
    vv_stack, vh_stack,
    ndvi_hist_min, ndvi_hist_max,
)
print(f"\nFeature cube shape: {feature_cube.shape}")
print(f"Features: NDVI_mean, NDVI_std, EVI_mean, NDWI_mean, VCI, VV, VH, VH/VV, GLCM×2, NDVI_peak, SOS, LGP, stage")

# Visualise
fig, axes = plt.subplots(2, 3, figsize=(14, 8))
fig.suptitle('Feature Engineering — Bhakra Canal Command, Punjab\nMeraCodeLikhDo | ISRO BAH 2026', fontsize=13)

im0 = axes[0,0].imshow(ndvi_stack[-1], cmap='RdYlGn', vmin=0, vmax=0.9)
axes[0,0].set_title('NDVI (latest composite)'); plt.colorbar(im0, ax=axes[0,0])

im1 = axes[0,1].imshow(evi_stack[-1], cmap='RdYlGn', vmin=0, vmax=0.8)
axes[0,1].set_title('EVI (latest composite)'); plt.colorbar(im1, ax=axes[0,1])

im2 = axes[0,2].imshow(vci_stack, cmap='RdYlGn', vmin=0, vmax=1)
axes[0,2].set_title('Vegetation Condition Index (VCI)'); plt.colorbar(im2, ax=axes[0,2])

im3 = axes[1,0].imshow(vv_stack[-1], cmap='Blues', vmin=-25, vmax=-5)
axes[1,0].set_title('SAR VV Backscatter (dB)'); plt.colorbar(im3, ax=axes[1,0])

im4 = axes[1,1].imshow(stage_map, cmap='tab10', vmin=0, vmax=4)
axes[1,1].set_title('Growth Stage Map')
patches = [mpatches.Patch(color=plt.cm.tab10(i/10), label=f'{i}:{n}') for i,n in stage_names.items()]
axes[1,1].legend(handles=patches, fontsize=7, loc='lower right')

axes[1,2].plot(dates, pheno['smoothed_ndvi'], 'g-o', linewidth=2, markersize=4)
axes[1,2].axhline(0.25, color='orange', linestyle='--', label='SOS threshold')
axes[1,2].set_title('Smoothed NDVI Time Series')
axes[1,2].set_xticks(dates[::4]); axes[1,2].set_xticklabels(dates[::4], rotation=45, fontsize=7)
axes[1,2].legend()

for ax in axes.flat[:5]: ax.axis('off') if ax != axes[1,2] else None
plt.tight_layout()
plt.savefig('02_feature_engineering.png', dpi=150, bbox_inches='tight')
plt.close()
print("\nSaved: 02_feature_engineering.png")
