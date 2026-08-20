"""
Phase 20 WebSocket test — validates /ws/feed still delivers correct envelope shape
with real model predictions (not mock). Mirrors what Phase 8's original WS test
confirmed: type/sensor_reading/risk_prediction fields present and valid per schema.
"""
import asyncio
import json

async def run_ws_test():
    try:
        import websockets
    except ImportError:
        print("websockets not installed — install with: pip install websockets")
        return

    PORT = 8001
    URI = f"ws://127.0.0.1:{PORT}/ws/feed"

    print(f"Connecting to {URI} ...")
    async with websockets.connect(URI) as ws:
        print("Connected. Collecting 3 messages ...\n")
        for i in range(3):
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(raw)

            print(f"--- Message {i+1} ---")
            print(json.dumps(msg, indent=2, default=str)[:600])  # truncate for readability
            print()

            # Envelope shape assertions (Phase 8 contract)
            assert msg.get("type") == "telemetry_update", f"Wrong type: {msg.get('type')}"
            assert "sensor_reading" in msg, "Missing sensor_reading"
            assert "risk_prediction" in msg, "Missing risk_prediction"
            assert "timestamp" in msg, "Missing top-level timestamp"

            sr = msg["sensor_reading"]
            rp = msg["risk_prediction"]

            # SensorReading schema fields
            for field in ["sensor_id", "zone_id", "timestamp", "displacement_mm_day",
                          "vibration", "pore_pressure", "strain", "rainfall_mm"]:
                assert field in sr, f"SensorReading missing field: {field}"

            # RiskPrediction schema fields
            for field in ["zone_id", "timestamp", "risk_level", "risk_score",
                          "displacement_velocity_mm_day", "model_version"]:
                assert field in rp, f"RiskPrediction missing field: {field}"

            # Semantic checks
            assert rp["risk_level"] in ("safe", "warning", "evacuation"), \
                f"Invalid risk_level: {rp['risk_level']}"
            assert 0.0 <= rp["risk_score"] <= 1.0, \
                f"risk_score out of range: {rp['risk_score']}"
            assert rp["model_version"] == "rf-v2-20260820", \
                f"Wrong model_version in WS payload: {rp['model_version']}"
            assert rp["displacement_velocity_mm_day"] == sr["displacement_mm_day"], \
                "displacement_velocity_mm_day != displacement_mm_day"

            print(f"  [OK] Message {i+1}: zone={rp['zone_id']}, "
                  f"risk_level={rp['risk_level']}, "
                  f"risk_score={rp['risk_score']:.4f}, "
                  f"model_version={rp['model_version']}")
            print()

    print("[OK] All 3 WebSocket messages passed schema + semantic validation.")
    print("Envelope shape identical to Phase 8 confirmed.")


if __name__ == "__main__":
    asyncio.run(run_ws_test())
