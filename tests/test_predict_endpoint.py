"""Phase 20 final combined smoke test — health + predict."""
import json, urllib.request

PORT = 8001

# /health
req = urllib.request.Request(f"http://127.0.0.1:{PORT}/health")
with urllib.request.urlopen(req, timeout=5) as r:
    h = json.loads(r.read())
    print("=== GET /health ===")
    print(json.dumps(h, indent=2))
    assert h["status"] == "ok", f"health status not ok: {h}"
    assert h["model_version"] == "rf-v2-20260820", f"wrong model_version: {h}"
    print("  [OK] status=ok, model_version=rf-v2-20260820")
    print()

# /predict — known evacuation row from test.csv idx=10
payload = {
    "sensor_id": "SNS-zone_11-01",
    "zone_id": "zone_11",
    "timestamp": "2026-06-03T00:00:00Z",
    "displacement_mm_day": 115.14,
    "vibration": 0.370,
    "pore_pressure": 102.09,
    "strain": 904.45,
    "rainfall_mm": 0.0,
}
data = json.dumps(payload).encode()
req2 = urllib.request.Request(
    f"http://127.0.0.1:{PORT}/predict",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req2, timeout=10) as r2:
    p = json.loads(r2.read())
    print("=== POST /predict ===")
    print(json.dumps(p, indent=2))
    print()

    live_risk = p["risk_level"]
    offline_risk = "evacuation"
    model_ver = p["model_version"]

    print(f"  Offline Phase 14 prediction: {offline_risk}")
    print(f"  Live /predict prediction:    {live_risk}")
    print(f"  model_version:               {model_ver}")
    print(f"  risk_score:                  {p['risk_score']}")
    print(f"  displacement_velocity_mm_day:{p['displacement_velocity_mm_day']}")
    print()

    assert live_risk == offline_risk, f"MISMATCH: offline={offline_risk}, live={live_risk}"
    assert model_ver == "rf-v2-20260820", f"wrong model_version: {model_ver}"
    assert p["displacement_velocity_mm_day"] == 115.14, f"velocity mismatch"
    assert 0.0 <= p["risk_score"] <= 1.0, "risk_score out of range"
    print("  [OK] All assertions passed — predictions match, schema valid")
