"""
Phase 25 verification script — boots the FastAPI app, hits /predict and /health,
asserts model_version == 'rf-v2-20260820'. No network, no real server process.

Ephemeral verification artifact; safe to delete after running.
"""
import sys
from pathlib import Path

# Ensure repo root is importable so backend.app / backend.routers resolve.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

EXPECTED_MODEL_VERSION = "rf-v2-20260820"

with TestClient(app) as client:
    # 1. /health
    health = client.get("/health").json()
    print("HEALTH:", health)
    assert health["model_version"] == EXPECTED_MODEL_VERSION, (
        f"/health model_version mismatch: {health['model_version']!r} != {EXPECTED_MODEL_VERSION!r}"
    )
    assert health["status"] == "ok"

    # 2. /predict -- minimum-valid SensorReading against a known zone
    sample_reading = {
        "sensor_id": "SNS-zone_01-01",
        "zone_id": "zone_01",
        "timestamp": "2026-06-15T00:00:00Z",
        "displacement_mm_day": 75.0,
        "vibration": 0.150,
        "pore_pressure": 65.0,
        "strain": 320.0,
        "rainfall_mm": 12.5,
    }
    predict = client.post("/predict", json=sample_reading).json()
    print("PREDICT:", predict)
    assert predict["model_version"] == EXPECTED_MODEL_VERSION, (
        f"/predict model_version mismatch: {predict['model_version']!r} != {EXPECTED_MODEL_VERSION!r}"
    )
    assert predict["zone_id"] == "zone_01"
    assert predict["risk_level"] in ("safe", "warning", "evacuation")
    assert 0.0 <= predict["risk_score"] <= 1.0

    # 3. /predict on a second zone to confirm same model_version propagates
    sample_reading_2 = dict(sample_reading, zone_id="zone_08", sensor_id="SNS-zone_08-01")
    predict_2 = client.post("/predict", json=sample_reading_2).json()
    print("PREDICT-2:", predict_2)
    assert predict_2["model_version"] == EXPECTED_MODEL_VERSION

print()
print(f"PASS: model_version == {EXPECTED_MODEL_VERSION!r} on /health and /predict")
