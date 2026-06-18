"""Quick smoke test for all backend modules."""
import sys, numpy as np
sys.path.insert(0, '.')

print("Testing imports...")
from app.core.config import settings
from app.data.demo_generator import COMPOSITE_DATES, generate_crop_map, generate_stress_map, generate_advisory_map
from app.models.water_deficit import compute_etc, compute_water_deficit
from app.models.stress_detector import detect_stress
from app.pipeline.feature_engineering import compute_ndvi, compute_vci, build_feature_cube
from app.services.nlg_service import generate_advisory_text_template

print(f"Config: {settings.APP_NAME} {settings.APP_VERSION}")
print(f"Composites: {len(COMPOSITE_DATES)}")

# Test demo data generation
crop_map_data = generate_crop_map()
assert len(crop_map_data["features"]) == 900
print(f"Crop map: {len(crop_map_data['features'])} features OK")

stress_data = generate_stress_map("2025-08-12")
assert len(stress_data["features"]) == 900
print(f"Stress map: OK")

adv_data = generate_advisory_map("2025-08-12")
assert len(adv_data["features"]) == 900
print(f"Advisory map: OK")

# Test ML models
H, W, T = 10, 10, 8
rng = np.random.default_rng(1)
nir = rng.uniform(0.2, 0.7, (T, H, W))
red = rng.uniform(0.05, 0.2, (T, H, W))
ndvi_stack = compute_ndvi(nir, red)
print(f"NDVI stack shape: {ndvi_stack.shape}")

et0 = rng.uniform(3, 6, (H, W))
crop = rng.integers(0, 9, (H, W))
stage = rng.integers(0, 5, (H, W))
etc = compute_etc(et0, crop, stage)
print(f"ETc mean: {etc.mean():.2f} mm/8-day")

# Test NLG
msg = generate_advisory_text_template("irrigate_now", "paddy_rice", "flowering_heading", 42.5, "HIGH")
assert "irrigate" in msg["hi"].lower() or len(msg["hi"]) > 50
print(f"NLG Hindi: {msg['hi'][:60]}...")
print(f"NLG English: {msg['en'][:60]}...")

print("\n[ALL SMOKE TESTS PASSED]")
