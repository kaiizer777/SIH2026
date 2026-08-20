"""
routers/rockfall.py -- Phase 21: Real physics-informed generator + alert-trigger logic.

Key contracts:
- build_prediction() is the single source of truth for feature assembly + inference.
  Both POST /predict and the WebSocket broadcast loop call it -- no duplicated logic.
- SAR lookup replicates Phase 12's sar_forward_fill() backward-fill semantics:
  merge_asof(direction="backward") on normalized date, per zone. A live reading's
  timestamp won't exactly match one of the 30 SAR acquisition dates, so we always
  take the nearest prior SAR date (same max staleness: 23 days verified in Phase 12).
- Feature vector assembled in the exact order from app.state.feature_order (JSON).
- Integer class decoded via app.state.label_encoding inverse map -- never hardcoded.
- model_version set from app.state.model_version -- never hardcoded in this file.

Phase 21 additions:
- _generate_mock_reading() removed. Reading generation now uses step_zone() from
  app.physics_generator, called with the zone's persistent ZoneGeneratorState stored
  in app.state.zone_generator_state.
- Alert-trigger logic: classify_alert() detects level transitions and fires AlertEvents.
  De-dup: a zone staying at the same level never fires more than 1 alert.
  Upgrade (into warning/evacuation): severity matches the new level.
  Downgrade (into a lower level): severity="advisory", message framed as informational
  not as a clearance command. See classify_alert() docstring for full policy.
- Broadcast loop advances one zone per tick (round-robin, cursor in app.state).
  Zone physics cursor advances every tick regardless of client count.
  Model inference + broadcast + alert logic run only when clients are connected.
- ConnectionManager.broadcast() already handles mid-broadcast disconnects correctly
  (try/except per connection, dead connections removed after the loop). Verified
  unchanged from Phase 8/20 -- no structural fix needed, test coverage added.
- Exception swallowing in broadcast loop tightened: exceptions are now logged via
  the module logger before continuing, so crashes are visible in server logs.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
import json
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, status

try:
    from backend.app.schemas import (
        AlertEvent,
        EVACUATION_DISPLACEMENT_MIN_MM_DAY,
        RiskLevel,
        RiskPrediction,
        SAFE_DISPLACEMENT_MAX_MM_DAY,
        SensorReading,
        WARNING_DISPLACEMENT_MAX_MM_DAY,
        WARNING_DISPLACEMENT_MIN_MM_DAY,
    )
    from backend.app.physics_generator import step_zone, ZONE_IDS
except ImportError:
    from app.schemas import (  # type: ignore
        AlertEvent,
        EVACUATION_DISPLACEMENT_MIN_MM_DAY,
        RiskLevel,
        RiskPrediction,
        SAFE_DISPLACEMENT_MAX_MM_DAY,
        SensorReading,
        WARNING_DISPLACEMENT_MAX_MM_DAY,
        WARNING_DISPLACEMENT_MIN_MM_DAY,
    )
    from app.physics_generator import step_zone, ZONE_IDS  # type: ignore


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection Manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """
    Manages active WebSocket connections for live sensor and risk telemetry feed.
    Accepts on connect, broadcasts to all active sockets, cleans up on disconnect.

    broadcast() is disconnect-safe: if a client disconnects mid-loop, the exception
    is caught per-connection, the dead socket is collected, and the loop continues
    for remaining clients. The failed connection is removed after the loop completes
    so no other client is affected. This design is preserved from Phase 8/20 and
    tested explicitly by tests/test_ws_disconnect.py.
    """
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict | str) -> None:
        if not self.active_connections:
            return
        payload = json.dumps(message) if isinstance(message, dict) else message
        disconnected = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception:
                disconnected.add(connection)
        for dead_conn in disconnected:
            self.active_connections.discard(dead_conn)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# SAR backward-fill lookup (single reading -- mirrors Phase 12's sar_forward_fill)
# ---------------------------------------------------------------------------

def _lookup_sar_features(
    zone_id: str,
    reading_timestamp: str,
    zone_features_df: pd.DataFrame,
) -> dict[str, float]:
    """
    For a single incoming reading, retrieve the most-recent SAR row for its zone
    whose date <= the reading's date (backward-fill, same semantics as Phase 12's
    merge_asof(direction='backward')).

    Args:
        zone_id: e.g. "zone_11"
        reading_timestamp: ISO-8601 string, e.g. "2026-06-03T00:00:00Z"
        zone_features_df: app.state.zone_features -- pre-sorted by (zone_id, _zf_date)

    Returns:
        dict with keys: slope, aspect, curvature, vv_backscatter, vh_backscatter, rainfall_mm

    Raises:
        KeyError: if zone_id not found in zone_features
        ValueError: if no SAR date exists on or before the reading's date
    """
    reading_dt = pd.to_datetime(reading_timestamp).normalize()
    if reading_dt.tzinfo is not None:
        reading_dt = reading_dt.tz_localize(None)

    zone_rows = zone_features_df[zone_features_df["zone_id"] == zone_id].copy()
    if zone_rows.empty:
        raise KeyError(f"zone_id '{zone_id}' not found in zone_features")

    valid = zone_rows[zone_rows["_zf_date"] <= reading_dt]
    if valid.empty:
        raise ValueError(
            f"No SAR acquisition on or before {reading_dt.date()} for zone '{zone_id}'. "
            f"Earliest available: {zone_rows['_zf_date'].min().date()}"
        )

    row = valid.iloc[-1]
    return {
        "slope":          float(row["slope"]),
        "aspect":         float(row["aspect"]),
        "curvature":      float(row["curvature"]),
        "vv_backscatter": float(row["vv_backscatter"]),
        "vh_backscatter": float(row["vh_backscatter"]),
        "rainfall_mm":    float(row["rainfall_mm"]),
    }


# ---------------------------------------------------------------------------
# Core prediction function -- single source of truth
# ---------------------------------------------------------------------------

def build_prediction(reading: SensorReading, app_state) -> RiskPrediction:
    """
    Assemble feature vector from SensorReading + static zone SAR features,
    run RF v2 inference, decode back to RiskLevel string, return RiskPrediction.

    Called by:
      - POST /predict  (synchronous per-request)
      - broadcast_sensor_feed_loop  (background loop tick)

    Never duplicates model-loading or feature-assembly logic.
    """
    model         = app_state.model
    feature_order = app_state.feature_order
    label_enc     = app_state.label_encoding
    zone_features = app_state.zone_features
    model_version = app_state.model_version

    inv_label_enc: dict[int, str] = {v: k for k, v in label_enc.items()}

    sar = _lookup_sar_features(reading.zone_id, reading.timestamp, zone_features)

    sensor_vals = {
        "displacement_mm_day": reading.displacement_mm_day,
        "vibration":           reading.vibration,
        "pore_pressure":       reading.pore_pressure,
        "strain":              reading.strain,
        "rainfall_mm":         reading.rainfall_mm,
    }

    all_vals = {**sensor_vals, **sar}

    feature_vec = pd.DataFrame([[all_vals[col] for col in feature_order]], columns=feature_order)

    pred_int: int = int(model.predict(feature_vec)[0])
    proba: np.ndarray = model.predict_proba(feature_vec)[0]

    risk_score = float(proba[pred_int])
    risk_label_str: str = inv_label_enc[pred_int]
    risk_level = RiskLevel(risk_label_str)

    return RiskPrediction(
        zone_id=reading.zone_id,
        timestamp=reading.timestamp,
        risk_level=risk_level,
        risk_score=round(risk_score, 6),
        displacement_velocity_mm_day=reading.displacement_mm_day,
        model_version=model_version,
    )


# ---------------------------------------------------------------------------
# Alert-trigger logic
# ---------------------------------------------------------------------------

_LEVEL_ORDER: dict[str, int] = {"safe": 0, "warning": 1, "evacuation": 2}
_ALERT_TRIGGER_LEVELS: frozenset[str] = frozenset({"warning", "evacuation"})

AlertType = Literal["upgrade", "downgrade"]


def classify_alert(old_level: str | None, new_level: str) -> AlertType | None:
    """
    Determine whether a risk level transition should fire an AlertEvent, and
    if so, whether it's an upgrade or a downgrade.

    Returns:
        "upgrade"   -- crossing INTO warning or evacuation from a lower level
        "downgrade" -- crossing DOWN from a higher alert level to a lower one
        None        -- no alert (same level = de-dup; or initial safe state)

    Audit trail policy:
        ALL transitions that represent a genuine state change are logged.
        Silence is reserved for:
          1. No change (de-dup): same level -> same level fires exactly 1 alert,
             at the tick of first entry. A zone in evacuation for 10 ticks produces
             exactly 1 alert at tick 1 and 0 alerts at ticks 2-10.
          2. Initial state settling into "safe" (None -> safe): the zone has never
             been in a dangerous state, so there is nothing to report.

        Downgrade transitions (evacuation->warning, *->safe) fire an "advisory"
        severity event. Rationale: silently dropping downgrade transitions creates
        an audit log that omits transitions, which is harder to defend under
        scrutiny than one that logs all changes with honest severity levels.
        The risk of a downgrade event being misread as an all-clear command is
        addressed by message wording and severity, not by omission.
        IMPORTANT: Do NOT add "clear", "safe to return", or "resolved" to any
        downgrade alert message -- the wording must read as informational only.

    Alert classification by transition:
        None -> safe       : None     (initial safe state, no prior danger)
        None -> warning    : upgrade
        None -> evacuation : upgrade
        safe -> warning    : upgrade
        safe -> evacuation : upgrade  (skipped warning -- one-tick jump)
        warning -> evacuation : upgrade
        evacuation -> warning : downgrade
        evacuation -> safe    : downgrade  (skipped warning on descent)
        warning -> safe       : downgrade
        * -> * (same level)   : None  (de-dup)
    """
    if new_level == old_level:
        return None  # de-dup: no repeated alert for sustained state

    old_rank = _LEVEL_ORDER.get(old_level, -1) if old_level is not None else -1
    new_rank = _LEVEL_ORDER[new_level]

    if new_rank > old_rank:
        # Escalation (includes None -> warning/evacuation as None has rank -1)
        if new_level in _ALERT_TRIGGER_LEVELS:
            return "upgrade"
        # new_level == "safe" and rank > old_rank: only possible if old_level is None
        # (None->safe). Per policy: no alert for initial safe state.
        return None
    else:
        # De-escalation
        if old_level in _ALERT_TRIGGER_LEVELS:
            return "downgrade"
        # old_level is None (shouldn't reach here since new_rank > old_rank would
        # catch that), or old_level == "safe" going to... same rank handled by de-dup.
        return None


def _build_alert_event(
    zone_id: str,
    old_level: str | None,
    new_level: str,
    alert_type: AlertType,
) -> AlertEvent:
    """
    Construct an AlertEvent for a detected risk level transition.

    Severity:
      - upgrade:   severity = new_level (so "warning" or "evacuation")
      - downgrade: severity = "advisory"  (explicitly lower, not actionable as stand-down)

    Message wording explicitly avoids "clear", "safe to return", or "resolved"
    on downgrade events. The message is informational only -- operators must
    independently verify before taking any action.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    alert_id = f"ALT-{zone_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}"

    if alert_type == "upgrade":
        severity = new_level  # "warning" or "evacuation"
        message = (
            f"Zone {zone_id} risk level increased to {new_level.upper()}. "
            f"Previous level: {old_level or 'unknown'}. Immediate review required."
        )
    else:  # downgrade
        severity = "advisory"
        message = (
            f"Zone {zone_id} risk level decreased to {new_level.upper()} "
            f"(from {old_level or 'unknown'}) -- continue monitoring, not a stand-down command. "
            f"Conditions may change. Independent verification required before any stand-down."
        )

    return AlertEvent(
        alert_id=alert_id,
        zone_id=zone_id,
        severity=severity,
        message=message,
        triggered_at=now_iso,
        acknowledged=False,
    )


# ---------------------------------------------------------------------------
# Background broadcast loop -- real physics generator + alert logic
# ---------------------------------------------------------------------------

async def broadcast_sensor_feed_loop(app, interval_seconds: float = 2.5) -> None:
    """
    Background worker: steps one zone per tick (round-robin across all 16 zones),
    runs it through the real RF v2 model, fires AlertEvents on threshold crossings,
    and broadcasts to all connected WebSocket clients.

    Zone stepping:
      - One zone is advanced per tick (not all 16), using a round-robin cursor
        stored in app.state.zone_tick_cursor.
      - Full cycle (all 16 zones) = 16 ticks * 2.5s = 40 seconds.
      - Physics cursor ALWAYS advances, regardless of whether clients are connected
        (keeps simulated time moving even during idle periods).
      - Model inference + broadcast + alert logic run only if active clients exist
        (avoids unnecessary CPU burn on model.predict() with no audience).

    Alert de-dup:
      - app.state.zone_last_risk_level[zone_id] tracks each zone's last known level.
      - classify_alert() fires at most 1 alert per transition event.
      - Updated unconditionally after every tick (even if no clients are connected)
        so state is accurate when the first client connects.

    Exception handling:
      - Per-tick exceptions are LOGGED (not silently swallowed) then loop continues.
        This prevents a single bad reading from crashing the entire background task
        while still making failures visible in server logs.
    """
    # Give lifespan a moment to fully initialize state before first tick
    await asyncio.sleep(0.1)

    while True:
        try:
            # --- Pick zone (round-robin, or single-zone if test override set) ---
            _force_zone_id = os.getenv("BROADCAST_FORCE_ZONE_ID", "").strip()
            if _force_zone_id:
                # Test override: restrict round-robin to one zone. Used by the
                # Phase 26 de-dup test to verify 5+ consecutive forced ticks
                # of the same zone produce exactly 1 alert. OFF by default.
                zone_id: str = _force_zone_id
            else:
                zone_ids: list[str] = ZONE_IDS
                cursor: int = app.state.zone_tick_cursor % len(zone_ids)
                zone_id: str = zone_ids[cursor]
                app.state.zone_tick_cursor = cursor + 1

            # --- Advance physics state (always, regardless of client count) ---
            state = app.state.zone_generator_state[zone_id]
            reading: SensorReading = step_zone(
                state,
                app.state.api_norm,
                app.state.rainfall_values,
                app.state.sim_dates,
            )

            if manager.active_connections:
                # --- Real model inference ---
                prediction: RiskPrediction = build_prediction(reading, app.state)

                # --- Broadcast telemetry_update ---
                telemetry_payload = {
                    "type": "telemetry_update",
                    "sensor_reading": reading.model_dump(),
                    "risk_prediction": prediction.model_dump(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await manager.broadcast(telemetry_payload)

                # --- Alert-trigger logic ---
                new_level: str = prediction.risk_level.value
                old_level: str | None = app.state.zone_last_risk_level.get(zone_id)
                alert_type = classify_alert(old_level, new_level)

                if alert_type is not None:
                    alert = _build_alert_event(zone_id, old_level, new_level, alert_type)
                    alert_payload = {
                        "type": "alert_event",
                        "alert": alert.model_dump(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    await manager.broadcast(alert_payload)
                    logger.info(
                        "ALERT [%s] zone=%s %s->%s severity=%s alert_id=%s",
                        alert_type, zone_id, old_level, new_level,
                        alert.severity, alert.alert_id,
                    )

                # --- Always update last known level ---
                app.state.zone_last_risk_level[zone_id] = new_level

            else:
                # No clients: still update last known level from the sensor reading
                # so that alert de-dup state stays current even during idle periods.
                generator_risk = reading.risk_level.value if reading.risk_level else "safe"
                app.state.zone_last_risk_level[zone_id] = generator_risk

        except Exception as exc:
            logger.exception(
                "Broadcast loop tick failed (zone_cursor=%d) -- continuing: %s",
                getattr(app.state, "zone_tick_cursor", -1),
                exc,
            )

        await asyncio.sleep(interval_seconds)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["Rockfall Telemetry & Prediction"])


@router.post(
    "/predict",
    response_model=RiskPrediction,
    status_code=status.HTTP_200_OK,
    summary="RF v2 Rockfall Risk Inference",
    description=(
        "Accepts a SensorReading, looks up static terrain/SAR features for the zone "
        "(backward-fill to nearest prior SAR acquisition date), assembles the 10-feature "
        "vector in trained column order, and returns a RiskPrediction from RF v2 "
        "(rf-v2-20260820.joblib). Model loaded once at startup via lifespan."
    ),
)
async def predict_rockfall(reading: SensorReading, request: Request) -> RiskPrediction:
    return build_prediction(reading, request.app.state)


@router.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket) -> None:
    """
    WebSocket feed broadcasting SensorReading + RiskPrediction (and AlertEvents)
    every interval_seconds. The background broadcast_sensor_feed_loop handles
    all message generation and delivery -- this handler just manages connect/disconnect.

    No immediate on-connect message is sent: the first telemetry tick arrives
    within interval_seconds (~2.5s), keeping the connect path simple and avoiding
    any race condition between this handler and the background loop both trying
    to step the same zone's generator state simultaneously.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket)
