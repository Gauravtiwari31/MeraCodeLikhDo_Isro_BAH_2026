"""
Notebook 04 — Phenology-Aware Stress Detection
=================================================
USP 4.2: True Stage-Level SAR+Optical Fusion
USP 4.3: Confidence-Aware Advisory (MC Dropout)
"""

import sys, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
sys.path.insert(0, str(Path('../backend').resolve()))

from app.models.stress_detector import (
    compute_ndvi_anomaly, detect_stress,
    STRESS_CLASSES, STRESS_PALETTE, STAGE_CONFIG,
)
from app.pipeline.feature_engineering import (
    compute_ndvi, compute_evi, compute_ndwi,
    compute_vci, compute_smi, assign_growth_stage_per_pixel,
)

# ── Simulate data ─────────────────────────────────────────────────────
H, W, T = 30, 30, 20
rng = np.random.default_rng(77)
t_arr = np.linspace(0, 1, T)

nir_s  = rng.uniform(0.2, 0.55, (T, H, W))
red_s  = rng.uniform(0.04, 0.18, (T, H, W))
green_s= rng.uniform(0.05, 0.12, (T, H, W))
vv_s   = rng.uniform(-20, -8, (T, H, W))
vh_s   = rng.uniform(-28, -12, (T, H, W))

for t in range(T):
    peak = 0.50 * np.exp(-((t_arr[t] - 0.55)**2) / (2 * 0.06))
    nir_s[t] += peak; red_s[t] -= peak * 0.3

ndvi_s  = compute_ndvi(nir_s, red_s)
ndwi_s  = compute_ndwi(green_s, nir_s)
ndvi_min = ndvi_s.min(axis=0) - rng.uniform(0.02, 0.1, (H, W))
ndvi_max = ndvi_s.max(axis=0) + rng.uniform(0.02, 0.1, (H, W))
hist_mean= ndvi_s.mean(axis=0) + rng.uniform(0.05, 0.15, (H, W))  # 'current' is below hist
hist_std = rng.uniform(0.02, 0.06, (H, W))

# Current (latest) composite
ndvi_cur  = ndvi_s[-1]
ndwi_cur  = ndwi_s[-1]
vci       = compute_vci(ndvi_cur, ndvi_min, ndvi_max)
smi       = compute_smi(vv_s[-1], vh_s[-1])
anomaly   = compute_ndvi_anomaly(ndvi_cur, hist_mean, hist_std)
stage_map = assign_growth_stage_per_pixel(ndvi_s, current_t=T-1)

# ── Stress detection with MC Dropout ─────────────────────────────────
print("=== Phenology-Aware Stress Detection ===")
print(f"USP 4.2: Stage-level SAR+Optical fusion")
print(f"USP 4.3: MC Dropout uncertainty quantification\n")

result = detect_stress(
    ndvi_current=ndvi_cur,
    ndwi_current=ndwi_cur,
    vci=vci,
    smi=smi,
    ndvi_anomaly=anomaly,
    stage_map=stage_map,
    n_mc_samples=30,
    mc_noise_std=0.025,
)

severity_map     = result["severity_map"]
stress_index     = result["stress_index"]
uncertainty      = result["uncertainty"]
confidence_flag  = result["confidence_flag"]

print(f"Stress Index: mean={stress_index.mean():.3f}, std={stress_index.std():.3f}")
print(f"Uncertainty:  mean={uncertainty.mean():.4f}, max={uncertainty.max():.4f}\n")

print("=== Stress Severity Distribution ===")
for sid, sname in STRESS_CLASSES.items():
    pct = (severity_map == sid).mean() * 100
    print(f"  {sname:15s}: {pct:.1f}%")

print("\n=== Stage-wise Stress Thresholds ===")
for stage, cfg in STAGE_CONFIG.items():
    th = cfg["vci_thresholds"]
    print(f"  {stage:20s}: severe<{th['severe']:.2f} | moderate<{th['moderate']:.2f} | mild<{th['mild']:.2f}")

# ── Visualize ─────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(14, 8))
fig.suptitle('Phenology-Aware Stress Detection — Stage-Level SAR+Optical Fusion\n'
             'USP 4.2+4.3 | ISRO BAH 2026', fontsize=12)

color_img = np.zeros((H, W, 3))
for sid, hc in STRESS_PALETTE.items():
    r,g,b = int(hc[1:3],16)/255, int(hc[3:5],16)/255, int(hc[5:7],16)/255
    color_img[severity_map==sid] = [r,g,b]

axes[0,0].imshow(color_img); axes[0,0].set_title('Stress Severity Map'); axes[0,0].axis('off')
im1 = axes[0,1].imshow(stress_index, cmap='RdYlGn_r', vmin=0, vmax=1)
axes[0,1].set_title('Continuous Stress Index'); plt.colorbar(im1, ax=axes[0,1]); axes[0,1].axis('off')
im2 = axes[0,2].imshow(uncertainty, cmap='hot', vmin=0, vmax=0.15)
axes[0,2].set_title('MC Dropout Uncertainty\n(USP 4.3)'); plt.colorbar(im2, ax=axes[0,2]); axes[0,2].axis('off')
im3 = axes[1,0].imshow(vci, cmap='RdYlGn', vmin=0, vmax=1)
axes[1,0].set_title('Vegetation Condition Index (VCI)'); plt.colorbar(im3, ax=axes[1,0]); axes[1,0].axis('off')
im4 = axes[1,1].imshow(anomaly, cmap='RdBu', vmin=-2, vmax=2)
axes[1,1].set_title('NDVI Anomaly\n(vs. historical baseline)'); plt.colorbar(im4, ax=axes[1,1]); axes[1,1].axis('off')
im5 = axes[1,2].imshow(confidence_flag, cmap='RdYlGn_r', vmin=0, vmax=2)
axes[1,2].set_title('Confidence Flag Map\n(0=HIGH, 1=MED, 2=LOW)'); plt.colorbar(im5, ax=axes[1,2]); axes[1,2].axis('off')

plt.tight_layout()
plt.savefig('04_stress_detection.png', dpi=150, bbox_inches='tight')
plt.close()
print('\nSaved: 04_stress_detection.png')
