"""
scripts/phase26_integration_test.py -- Phase 26 Full Integration Test (automated).

Connects to /ws/feed via fastapi.testclient.TestClient (no separate uvicorn
process), consumes a bounded number of ticks (not `while True`), and asserts
that BOTH:

  1. `telemetry_update` envelope arrives with schema-valid payload
     (SensorReading + RiskPrediction matching backend/app/schemas.py)
  2. `alert_event` envelope arrives with schema-valid payload
     (AlertEvent matching backend/app/schemas.py), and that an evacuation
     AlertEvent fires within the bounded window.

Pattern follows WORK.md Phase 26 (the TestClient.websocket_connect snippet
verified against FastAPI's own docs, Aug 2026) and uses the FORCE_EVAC_ZONE
env-var debug override from app.physics_generator to deterministically force
an evacuation crossing -- the real Fukuzono generator won't reliably produce
one in a short test window.

Run from repo root:
    cd backend
    FORCE_EVAC_ZONE=zone_01 python ../scripts/phase26_integration_test.py

Or, with a custom tick budget:
    FORCE_EVAC_ZONE=zone_01 PHASE26_TICK_BUDGET=40 python ../scripts/phase26_integration_test.py
"""
from __future__ import annotations

import os
import sys
import textwrap
import time
from pathlib import Path

# Ensure repo root + backend/ are importable for `from main import app` and
# `from app.schemas import ...`. Running this script as `python scripts/...`
# needs the repo root on sys.path.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

# Apply the env-var BEFORE importing the app so the override is live for
# the first broadcast loop tick.
os.environ.setdefault("FORCE_EVAC_ZONE", "zone_01")

# Speed up the broadcast loop for the test so the tick budget is reasonable.
# 0.25s/tick * 64 ticks = 16s, enough to see zone_01 hit 4 times (4 of 16
# zones in round-robin). Default broadcast interval is 2.5s, which would
# make 16 ticks = 40s; the test budget default of 64 ticks at 0.25s = 16s.
os.environ.setdefault("BROADCAST_INTERVAL_SECONDS", "0.25")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from app.schemas import AlertEvent, RiskPrediction, SensorReading  # noqa: E402

EXPECTED_MODEL_VERSION = "rf-v2-20260820"

# Bounded tick budget. Not `while True` -- a hanging test is the worst
# failure mode for a CI gate. 64 ticks = 4 full round-robin cycles through
# 16 zones, enough to observe multiple visits to the forced zone.
TICK_BUDGET = int(os.environ.get("PHASE26_TICK_BUDGET", "64"))


def _validate_telemetry_update(msg: dict) -> None:
    """Validate one telemetry_update envelope against backend/app/schemas.py."""
    assert isinstance(msg, dict), f"telemetry_update payload not dict: {type(msg)}"
    assert msg.get("type") == "telemetry_update", f"wrong type: {msg.get('type')!r}"

    for k in ("sensor_reading", "risk_prediction", "timestamp"):
        assert k in msg, f"telemetry_update missing top-level key: {k!r}"

    # Schema-validate against the pydantic models. This is the strongest
    # "matches backend/app/schemas.py" assertion -- pydantic will reject
    # missing fields, wrong types, and out-of-range values.
    sr = SensorReading.model_validate(msg["sensor_reading"])
    rp = RiskPrediction.model_validate(msg["risk_prediction"])

    # Cross-field invariants not expressible in pydantic alone.
    assert rp.zone_id == sr.zone_id, (
        f"zone_id mismatch: rp={rp.zone_id} sr={sr.zone_id}"
    )
    assert rp.displacement_velocity_mm_day == sr.displacement_mm_day, (
        f"velocity mismatch: rp={rp.displacement_velocity_mm_day} sr={sr.displacement_mm_day}"
    )
    assert rp.model_version == EXPECTED_MODEL_VERSION, (
        f"model_version mismatch: {rp.model_version!r} != {EXPECTED_MODEL_VERSION!r}"
    )
    assert rp.risk_level.value in {"safe", "warning", "evacuation"}, (
        f"invalid risk_level: {rp.risk_level!r}"
    )
    assert 0.0 <= rp.risk_score <= 1.0, f"risk_score out of range: {rp.risk_score}"


def _validate_alert_event(msg: dict) -> AlertEvent:
    """Validate one alert_event envelope against backend/app/schemas.py."""
    assert isinstance(msg, dict), f"alert_event payload not dict: {type(msg)}"
    assert msg.get("type") == "alert_event", f"wrong type: {msg.get('type')!r}"

    for k in ("alert", "timestamp"):
        assert k in msg, f"alert_event missing top-level key: {k!r}"

    # Schema-validate against the pydantic model.
    alert = AlertEvent.model_validate(msg["alert"])
    assert alert.severity in {"warning", "evacuation", "advisory"}, (
        f"invalid alert severity: {alert.severity!r}"
    )
    assert len(alert.alert_id) > 0
    assert len(alert.zone_id) > 0
    assert len(alert.message) > 0
    assert alert.acknowledged is False
    return alert


def run_integration_test() -> int:
    """
    Returns 0 on pass, 1 on fail. Captures:
      - count of telemetry_update envelopes
      - count of alert_event envelopes
      - timestamp of first message received (for round-trip latency)
      - timestamp of FIRST alert received (for time-to-alert)
    """
    telemetry_count = 0
    alert_count = 0
    first_alert: AlertEvent | None = None
    first_msg_received_at: float | None = None
    first_alert_received_at: float | None = None
    first_telemetry_received_at: float | None = None
    last_msg_received_at: float | None = None
    last_alert: AlertEvent | None = None
    zone_01_alerts: list[AlertEvent] = []
    all_alerts: list[AlertEvent] = []
    errors: list[str] = []

    print("=" * 72)
    print("Phase 26 Full Integration Test -- TestClient-based, bounded loop")
    print("=" * 72)
    print(f"  FORCE_EVAC_ZONE       = {os.environ.get('FORCE_EVAC_ZONE')!r}")
    print(f"  BROADCAST_INTERVAL    = {os.environ.get('BROADCAST_INTERVAL_SECONDS')!r}s")
    print(f"  PHASE26_TICK_BUDGET   = {TICK_BUDGET}")
    print(f"  EXPECTED_MODEL_VERSION= {EXPECTED_MODEL_VERSION}")
    print()

    test_start = time.time()
    with TestClient(app) as client:
        # Quick sanity check on /health before opening the WebSocket.
        health = client.get("/health").json()
        assert health["model_version"] == EXPECTED_MODEL_VERSION, health
        assert health["status"] == "ok"
        print(f"  /health: {health}")
        print()

        with client.websocket_connect("/ws/feed") as ws:
            print(f"  WebSocket connected. Consuming up to {TICK_BUDGET} messages ...")
            for tick in range(TICK_BUDGET):
                msg = ws.receive_json()
                now = time.time()
                if first_msg_received_at is None:
                    first_msg_received_at = now
                last_msg_received_at = now

                msg_type = msg.get("type")
                if msg_type == "telemetry_update":
                    try:
                        _validate_telemetry_update(msg)
                    except AssertionError as e:
                        errors.append(f"tick {tick} telemetry validation failed: {e}")
                        break
                    telemetry_count += 1
                    if first_telemetry_received_at is None:
                        first_telemetry_received_at = now
                    if telemetry_count <= 3 or telemetry_count % 16 == 0:
                        rp = msg["risk_prediction"]
                        sr = msg["sensor_reading"]
                        print(
                            f"    [t={tick:03d}] telemetry_update: zone={rp['zone_id']}, "
                            f"risk={rp['risk_level']}, score={rp['risk_score']:.3f}, "
                            f"disp={sr['displacement_mm_day']:.1f} mm/day"
                        )
                elif msg_type == "alert_event":
                    try:
                        alert = _validate_alert_event(msg)
                    except AssertionError as e:
                        errors.append(f"tick {tick} alert validation failed: {e}")
                        break
                    alert_count += 1
                    all_alerts.append(alert)
                    if alert.zone_id == os.environ.get("FORCE_EVAC_ZONE", "zone_01"):
                        zone_01_alerts.append(alert)
                    if first_alert is None:
                        first_alert = alert
                        first_alert_received_at = now
                    last_alert = alert
                    print(
                        f"    [t={tick:03d}] *** ALERT  zone={alert.zone_id}, "
                        f"severity={alert.severity}, alert_id={alert.alert_id}"
                    )
                    print(f"             message: {alert.message}")
                else:
                    errors.append(f"tick {tick}: unknown message type: {msg_type!r}")
                    break

    test_end = time.time()

    # --- Compute latencies ---
    # Note: time-to-first-msg measures the WS pipeline only. End-to-end
    # (reading generated -> WS broadcast) is implicitly included because the
    # broadcast loop's interval is the dominant delay.
    test_duration = test_end - test_start
    time_to_first_msg = (
        first_msg_received_at - test_start if first_msg_received_at else None
    )
    time_to_first_alert = (
        first_alert_received_at - test_start if first_alert_received_at else None
    )

    print()
    print("=" * 72)
    print("Phase 26 Test Summary")
    print("=" * 72)
    print(f"  test duration              = {test_duration:.2f}s")
    print(f"  tick budget                = {TICK_BUDGET}")
    print(f"  telemetry_update received  = {telemetry_count}")
    print(f"  alert_event received       = {alert_count}")
    print(f"  time-to-first-message      = "
          f"{time_to_first_msg:.3f}s" if time_to_first_msg is not None else "  time-to-first-message      = N/A")
    print(f"  time-to-first-alert        = "
          f"{time_to_first_alert:.3f}s" if time_to_first_alert is not None else "  time-to-first-alert        = N/A (no alert)")
    print()
    print(f"  All alerts:")
    for a in all_alerts:
        print(f"    zone={a.zone_id:8s} severity={a.severity:12s} alert_id={a.alert_id}")
    print()

    # --- Assertions ---
    failed = False

    if errors:
        print("FAIL: Errors during message processing:")
        for e in errors:
            print(f"  - {e}")
        failed = True

    if telemetry_count == 0:
        print("FAIL: No telemetry_update envelopes received in tick budget")
        failed = True
    else:
        print(f"[OK] Received {telemetry_count} schema-valid telemetry_update envelopes")

    if alert_count == 0:
        print("FAIL: No alert_event envelopes received in tick budget")
        failed = True
    else:
        print(f"[OK] Received {alert_count} schema-valid alert_event envelopes")

    if first_alert is not None and first_alert.severity != "evacuation":
        print(f"FAIL: First alert severity={first_alert.severity}, expected evacuation")
        failed = True
    elif first_alert is not None:
        print(f"[OK] First alert severity=evacuation (zone={first_alert.zone_id})")

    if zone_01_alerts and len(zone_01_alerts) == 1:
        print(f"[OK] Forced zone produced exactly 1 alert across multiple ticks (de-dup holds)")
    elif zone_01_alerts and len(zone_01_alerts) > 1:
        print(f"FAIL: Forced zone produced {len(zone_01_alerts)} alerts -- de-dup violated")
        failed = True
    else:
        print(f"INFO: No alerts on forced zone yet (test budget may be too small)")

    print()
    if failed:
        print("[FAIL] Phase 26 integration test FAILED.")
        return 1
    print("[PASS] Phase 26 integration test passed.")
    return 0


# ---------------------------------------------------------------------------
# Phase 26 sub-tests: forced-evacuation de-dup, reconnect, dashboard
# ---------------------------------------------------------------------------

def run_dedup_test() -> int:
    """
    Force evacuation state on a single zone for 5+ CONSECUTIVE ticks (round-robin
    restricted to that zone via BROADCAST_FORCE_ZONE_ID) and confirm exactly
    1 AlertEvent fires, not 5.
    """
    os.environ["FORCE_EVAC_ZONE"] = "zone_01"
    os.environ["BROADCAST_FORCE_ZONE_ID"] = "zone_01"
    os.environ["BROADCAST_INTERVAL_SECONDS"] = "0.25"

    # Re-import the app to pick up the new env vars. We must close any previous
    # TestClient and re-create the app, but TestClient is one-shot. So we
    # spawn a fresh Python subprocess for each sub-test.
    import subprocess

    dedup_script = textwrap.dedent(
        """
        import os, sys, time
        from pathlib import Path
        sys.path.insert(0, r'BACKEND_DIR')
        os.environ['FORCE_EVAC_ZONE'] = 'zone_01'
        os.environ['BROADCAST_FORCE_ZONE_ID'] = 'zone_01'
        os.environ['BROADCAST_INTERVAL_SECONDS'] = '0.25'
        from fastapi.testclient import TestClient
        from main import app
        from app.schemas import AlertEvent

        BUDGET = 8  # 8 consecutive zone_01 ticks
        per_tick_alerts = []  # list of (tick, alert_dict_or_None)
        with TestClient(app) as client:
            with client.websocket_connect('/ws/feed') as ws:
                for tick in range(BUDGET):
                    msg = ws.receive_json()
                    if msg.get('type') == 'alert_event':
                        per_tick_alerts.append((tick, AlertEvent.model_validate(msg['alert'])))
                    else:
                        per_tick_alerts.append((tick, None))

        # Only one alert expected across all 8 ticks (the first crossing into evac).
        # Note: the FIRST WS message is a telemetry_update (broadcast happens before
        # the alert build/broadcast in the loop), so the alert appears at the next
        # iteration's alert_event envelope, which can land on any of the 8 ticks
        # after the initial telemetry. We just need: exactly 1 alert total, and
        # that alert's severity is "evacuation".
        alert_count = sum(1 for _, a in per_tick_alerts if a is not None)
        only_alert = next((a for _, a in per_tick_alerts if a is not None), None)
        print(f'  Total alerts in {BUDGET} consecutive forced-evac ticks: {alert_count}')
        for t, a in per_tick_alerts:
            if a is not None:
                print(f'    tick={t}: alert severity={a.severity} zone={a.zone_id} id={a.alert_id}')
        if alert_count == 1 and only_alert is not None and only_alert.severity == 'evacuation':
            print('  [OK] De-dup holds: exactly 1 alert in 8 consecutive forced-evac ticks')
            sys.exit(0)
        print('  [FAIL] De-dup violated')
        sys.exit(1)
        """
    ).replace("BACKEND_DIR", str(_REPO_ROOT / "backend"))

    print()
    print("=" * 72)
    print("Phase 26 Sub-test: Alert De-dup (5+ consecutive forced-evac ticks)")
    print("=" * 72)
    print(f"  FORCE_EVAC_ZONE=zone_01, BROADCAST_FORCE_ZONE_ID=zone_01, BUDGET=8")

    result = subprocess.run(
        [sys.executable, "-c", dedup_script],
        cwd=str(_REPO_ROOT / "backend"),
        capture_output=True,
        text=True,
        timeout=60,
    )
    print(result.stdout)
    if result.stderr:
        # Filter out the deprecation warning
        for line in result.stderr.splitlines():
            if "StarletteDeprecationWarning" in line or "httpx2" in line:
                continue
            print(f"  [stderr] {line}")
    return result.returncode


def run_reconnect_test() -> int:
    """
    Open WS1, receive messages, forcefully close, open WS2, verify clean
    ConnectionManager state (no leak, no duplicate broadcast) and that WS2
    receives messages normally.
    """
    os.environ["BROADCAST_INTERVAL_SECONDS"] = "0.25"
    # Don't force evac here -- the reconnect test is about connection lifecycle,
    # not alert content. Just need the broadcast loop running.
    os.environ.pop("FORCE_EVAC_ZONE", None)
    os.environ.pop("BROADCAST_FORCE_ZONE_ID", None)

    import subprocess

    reconnect_script = textwrap.dedent(
        """
        import os, sys, time
        from pathlib import Path
        sys.path.insert(0, r'BACKEND_DIR')
        os.environ['BROADCAST_INTERVAL_SECONDS'] = '0.25'
        from fastapi.testclient import TestClient
        from main import app
        from routers.rockfall import manager

        BUDGET_PER_CONNECTION = 5
        with TestClient(app) as client:
            # --- Phase A: open WS1, receive some messages ---
            print('  [Phase A] Open WS1, receive {BUDGET} messages ...')
            with client.websocket_connect('/ws/feed') as ws1:
                # Wait briefly for the WS to be registered in manager
                time.sleep(0.1)
                size_with_ws1 = len(manager.active_connections)
                print(f'    manager.active_connections after WS1 connect = {size_with_ws1}')

                ws1_messages = []
                for _ in range(BUDGET_PER_CONNECTION):
                    ws1_messages.append(ws1.receive_json())
                print(f'    WS1 received {len(ws1_messages)} messages')
                last_msg_id_ws1 = id(ws1_messages[-1])

            # WS1 forcibly closed (context manager exit). Give the broadcast
            # loop a moment to attempt a send to the dead socket, triggering
            # the cleanup path in ConnectionManager.broadcast().
            print('  [Phase A] WS1 closed; sleeping 0.6s for cleanup ...')
            time.sleep(0.6)
            size_after_ws1_close = len(manager.active_connections)
            print(f'    manager.active_connections after WS1 close = {size_after_ws1_close}')

            # --- Phase B: open WS2, verify it gets messages ---
            print('  [Phase B] Open WS2, receive {BUDGET} messages ...')
            with client.websocket_connect('/ws/feed') as ws2:
                time.sleep(0.1)
                size_with_ws2 = len(manager.active_connections)
                print(f'    manager.active_connections after WS2 connect = {size_with_ws2}')

                ws2_messages = []
                for _ in range(BUDGET_PER_CONNECTION):
                    ws2_messages.append(ws2.receive_json())
                print(f'    WS2 received {len(ws2_messages)} messages')

        # All connections closed
        size_after_all = len(manager.active_connections)
        print(f'    manager.active_connections after all WS closed = {size_after_all}')

        # --- Assertions ---
        passed = True
        if size_with_ws1 != 1:
            print(f'  [FAIL] Expected 1 connection with WS1, got {size_with_ws1}')
            passed = False
        else:
            print('  [OK] 1 connection registered with WS1')

        if size_after_ws1_close != 0:
            print(f'  [FAIL] Expected 0 connections after WS1 close (no leak), got {size_after_ws1_close}')
            passed = False
        else:
            print('  [OK] 0 connections after WS1 close -- no leak')

        if size_with_ws2 != 1:
            print(f'  [FAIL] Expected 1 connection with WS2, got {size_with_ws2}')
            passed = False
        else:
            print('  [OK] 1 connection registered with WS2 (clean state)')

        if len(ws2_messages) != BUDGET_PER_CONNECTION:
            print(f'  [FAIL] WS2 received {len(ws2_messages)} messages, expected {BUDGET_PER_CONNECTION}')
            passed = False
        else:
            print(f'  [OK] WS2 received {BUDGET_PER_CONNECTION} messages normally')

        if size_after_all != 0:
            print(f'  [FAIL] Expected 0 connections after all WS closed, got {size_after_all}')
            passed = False
        else:
            print('  [OK] 0 connections after all WS closed')

        if passed:
            print('  [OK] Reconnect test passed -- no leak, no duplicate, clean state')
            sys.exit(0)
        print('  [FAIL] Reconnect test FAILED')
        sys.exit(1)
        """
    ).replace("BACKEND_DIR", str(_REPO_ROOT / "backend")).replace("{BUDGET}", str(BUDGET_PER_CONNECTION := 5))

    print()
    print("=" * 72)
    print("Phase 26 Sub-test: Reconnect (forceful close + clean reconnect)")
    print("=" * 72)

    result = subprocess.run(
        [sys.executable, "-c", reconnect_script],
        cwd=str(_REPO_ROOT / "backend"),
        capture_output=True,
        text=True,
        timeout=60,
    )
    print(result.stdout)
    if result.stderr:
        for line in result.stderr.splitlines():
            if "StarletteDeprecationWarning" in line or "httpx2" in line:
                continue
            print(f"  [stderr] {line}")
    return result.returncode


if __name__ == "__main__":
    rc1 = run_integration_test()
    rc2 = run_dedup_test()
    rc3 = run_reconnect_test()

    print()
    print("=" * 72)
    print("Phase 26 Final Verdict")
    print("=" * 72)
    print(f"  Integration test: {'PASS' if rc1 == 0 else 'FAIL'} (rc={rc1})")
    print(f"  De-dup test:      {'PASS' if rc2 == 0 else 'FAIL'} (rc={rc2})")
    print(f"  Reconnect test:   {'PASS' if rc3 == 0 else 'FAIL'} (rc={rc3})")
    sys.exit(0 if (rc1 == 0 and rc2 == 0 and rc3 == 0) else 1)
