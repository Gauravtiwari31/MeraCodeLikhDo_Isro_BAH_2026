"""
Notebook 05 — Water Deficit Estimation & Irrigation Advisory
=============================================================
FAO-56 ETc method + Advisory Rule Engine + Canal Command Optimizer
USP 4.3: Confidence-Aware Advisory
USP 4.5: Canal Command Water-Budget Optimizer  
USP 4.4: Multilingual LLG Delivery
"""

import sys, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
sys.path.insert(0, str(Path('../backend').resolve()))

from app.models.water_deficit import (
    compute_etc, compute_water_deficit, generate_advisory_map,
    aggregate_to_canal_outlets,
    ADVISORY_CLASSES, ADVISORY_PALETTE, ADVISORY_DESCRIPTIONS,
    FAO56_KC,
)
from app.services.nlg_service import generate_advisory_text_template

# ── Simulate inputs ───────────────────────────────────────────────────
H, W = 30, 30
rng = np.random.default_rng(55)

# ET0 (reference ET) — from ERA5/CHIRPS, ~3.5–6 mm/day in Punjab kharif
et0 = rng.uniform(3.5, 6.0, (H, W))

# Crop map: mostly paddy (1) in north, cotton (4) in south
crop_map = np.ones((H, W), dtype=np.int32)
crop_map[H//2:, :] = 4   # cotton in south half

# Growth stage: flowering for paddy, vegetative for cotton
stage_map = np.full((H, W), 3, dtype=np.int32)   # flowering
stage_map[H//2:, :] = 2                           # vegetative

# Effective rainfall (mm/8-day) — lower in drier areas
rainfall = rng.uniform(2, 18, (H, W))

# Actual ET from remote sensing (from Penman-Monteith or SEBS) 
actual_et = et0 * rng.uniform(0.6, 0.95, (H, W)) * 8  # mm/period

# Confidence flags from stress detector
confidence_flag = rng.choice([0, 1, 2], size=(H, W), p=[0.55, 0.30, 0.15])

# ── FAO-56 ETc ───────────────────────────────────────────────────────
print("=== FAO-56 Crop Water Demand (ETc) ===")
etc = compute_etc(et0, crop_map, stage_map, period_days=8)
print(f"ETc (mm/8-day): mean={etc.mean():.1f}, min={etc.min():.1f}, max={etc.max():.1f}")

print("\nFAO-56 Kc values used (sample):")
for crop, stages in list(FAO56_KC.items())[:4]:
    print(f"  {crop:12s}: {stages}")

# ── Water Deficit ─────────────────────────────────────────────────────
deficit = compute_water_deficit(etc, rainfall, actual_et)
print(f"\n=== Water Deficit ===")
print(f"Deficit (mm/8-day): mean={deficit.mean():.1f}, min={deficit.min():.1f}, max={deficit.max():.1f}")

# ── Advisory map ─────────────────────────────────────────────────────
print("\n=== Irrigation Advisory Map ===")
adv_result = generate_advisory_map(deficit, stage_map, confidence_flag)
adv_map = adv_result["advisory_map"]

for cls, label in ADVISORY_CLASSES.items():
    pct = (adv_map == cls).mean() * 100
    print(f"  {label:14s}: {pct:.1f}%  — {ADVISORY_DESCRIPTIONS[cls]}")

# ── Canal Command Optimizer (USP 4.5) ─────────────────────────────────
print("\n=== Canal Command Water-Budget Optimizer (USP 4.5) ===")

# Define 6 simulated canal outlets as row strips
outlets = [
    {"outlet_id": f"BO-{i+1:02d}", "name": f"Bhakra Outlet {i+1} — Punjab Sector {i+1}",
     "pixel_mask": (np.arange(H)[:, None] >= (i*5)) & (np.arange(H)[:, None] < ((i+1)*5)) &
                   (np.ones((H, W), dtype=bool))}
    for i in range(6)
]

outlet_priorities = aggregate_to_canal_outlets(adv_map, deficit, outlets)
print(f"{'Rank':<5} {'Outlet':<35} {'Deficit':>10} {'Irrigate Now%':>14} {'Priority':>10}")
print("-" * 80)
for o in outlet_priorities:
    print(f"#{o['priority_rank']:<4} {o['outlet_name']:<35} {o['mean_deficit_mm']:>8.1f}mm "
          f"  {o['irrigate_now_pct']:>10.1f}%   {o['priority_score']:>8.1f}")

# ── Multilingual Advisory (USP 4.4) ───────────────────────────────────
print("\n=== Multilingual Advisory (USP 4.4) ===")
advisory_text = generate_advisory_text_template(
    advisory_class="irrigate_now",
    crop_name="paddy_rice",
    growth_stage="flowering_heading",
    deficit_mm=deficit.max(),
    confidence_label="HIGH",
    language="hi",
)
print("Hindi:")
print(advisory_text["hi"])
print("\nEnglish:")
print(advisory_text["en"])
print("\nSMS (160 chars):")
print(advisory_text["sms_hi"])

# ── Visualize ─────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('Water Deficit & Irrigation Advisory\nFAO-56 ETc + Advisory Rule Engine | ISRO BAH 2026', fontsize=12)

color_img = np.zeros((H, W, 3))
for cls, hc in ADVISORY_PALETTE.items():
    r,g,b = int(hc[1:3],16)/255, int(hc[3:5],16)/255, int(hc[5:7],16)/255
    color_img[adv_map==cls] = [r,g,b]

axes[0].imshow(color_img); axes[0].set_title('Irrigation Advisory Map'); axes[0].axis('off')
im1 = axes[1].imshow(deficit, cmap='RdYlBu_r', vmin=0, vmax=60)
axes[1].set_title('Water Deficit (mm/8-day)'); plt.colorbar(im1, ax=axes[1]); axes[1].axis('off')
im2 = axes[2].imshow(etc, cmap='YlOrRd', vmin=20, vmax=65)
axes[2].set_title('ETc — Crop Water Demand\n(FAO-56 method)'); plt.colorbar(im2, ax=axes[2]); axes[2].axis('off')

plt.tight_layout()
plt.savefig('05_water_deficit_advisory.png', dpi=150, bbox_inches='tight')
plt.close()
print('\nSaved: 05_water_deficit_advisory.png')
print('\nAll notebooks complete. MeraCodeLikhDo pipeline demonstrated end-to-end.')
