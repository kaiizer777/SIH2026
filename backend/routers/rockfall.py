import asyncio
from datetime import datetime, timezone
import json
import random
from typing import Optional, Tuple
from fastapi import APIRouter, Body, WebSocket, WebSocketDisconnect, status

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
except ImportError:
    from app.schemas import (
        AlertEvent,
        EVACUATION_DISPLACEMENT_MIN_MM_DAY,
        RiskLevel,
        RiskPrediction,
        SAFE_DISPLACEMENT_MAX_MM_DAY,
        SensorReading,
        WARNING_DISPLACEMENT_MAX_MM_DAY,
        WARNING_DISPLACEMENT_MIN_MM_DAY,
    )

# --- Connection Manager for WebSocket Streaming ---
class ConnectionManager:
    """
    Manages active WebSocket connections for live sensor and risk telemetry feed.
    Accepts on connect, broadcasts to all active sockets, cleans up on disconnect.
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


# --- Mock Inference & Data Generation Utilities ---
# Target class distribution matching 2026 physics-informed rockfall study:
# Low (Safe): 60% | Medium (Warning): 25% | High (Evacuation): 15%
RISK_LEVEL_CHOICES = [RiskLevel.SAFE, RiskLevel.WARNING, RiskLevel.EVACUATION]
RISK_LEVEL_WEIGHTS = [0.60, 0.25, 0.15]


def generate_mock_reading_and_prediction(
    zone_id: Optional[str] = None
) -> Tuple[RiskPrediction, SensorReading]:
    """
    Generates a realistic (SensorReading, RiskPrediction) pair adhering strictly
    to the 60/25/15 target distribution and grounded SSR velocity thresholds.
    """
    target_zone = zone_id or random.choice([f"zone_{i:02d}" for i in range(1, 17)])
    now_iso = datetime.now(timezone.utc).isoformat()

    # Weighted selection (Low 60%, Medium 25%, High 15%)
    selected_risk: RiskLevel = random.choices(
        RISK_LEVEL_CHOICES,
        weights=RISK_LEVEL_WEIGHTS,
        k=1
    )[0]

    if selected_risk == RiskLevel.SAFE:
        # Safe: 0–50 mm/day
        velocity = round(random.uniform(0.5, SAFE_DISPLACEMENT_MAX_MM_DAY - 0.5), 2)
        score = round(random.uniform(0.02, 0.35), 4)
        vibration = round(random.uniform(0.01, 0.10), 3)
        pore_pressure = round(random.uniform(30.0, 70.0), 2)
        strain = round(random.uniform(50.0, 250.0), 2)
        rainfall = round(random.uniform(0.0, 5.0), 2)
    elif selected_risk == RiskLevel.WARNING:
        # Warning: 50–120 mm/day
        velocity = round(random.uniform(WARNING_DISPLACEMENT_MIN_MM_DAY, WARNING_DISPLACEMENT_MAX_MM_DAY - 0.5), 2)
        score = round(random.uniform(0.40, 0.74), 4)
        vibration = round(random.uniform(0.11, 0.35), 3)
        pore_pressure = round(random.uniform(70.0, 130.0), 2)
        strain = round(random.uniform(250.0, 650.0), 2)
        rainfall = round(random.uniform(5.0, 25.0), 2)
    else:
        # Evacuation: >120 mm/day
        velocity = round(random.uniform(EVACUATION_DISPLACEMENT_MIN_MM_DAY + 0.5, 260.0), 2)
        score = round(random.uniform(0.75, 0.99), 4)
        vibration = round(random.uniform(0.36, 0.90), 3)
        pore_pressure = round(random.uniform(130.0, 250.0), 2)
        strain = round(random.uniform(650.0, 1600.0), 2)
        rainfall = round(random.uniform(25.0, 95.0), 2)

    prediction = RiskPrediction(
        zone_id=target_zone,
        timestamp=now_iso,
        risk_level=selected_risk,
        risk_score=score,
        displacement_velocity_mm_day=velocity,
        model_version="v1.0.0-mock-xgb",
    )

    reading = SensorReading(
        sensor_id=f"SNS-{target_zone}-01",
        zone_id=target_zone,
        timestamp=now_iso,
        displacement_mm_day=velocity,
        vibration=vibration,
        pore_pressure=pore_pressure,
        strain=strain,
        rainfall_mm=rainfall,
    )

    return prediction, reading


async def broadcast_sensor_feed_loop(interval_seconds: float = 2.5) -> None:
    """Background worker broadcasting mock sensor+prediction pairs to all connected WebSocket clients."""
    while True:
        try:
            if manager.active_connections:
                prediction, reading = generate_mock_reading_and_prediction()
                payload = {
                    "type": "telemetry_update",
                    "sensor_reading": reading.model_dump(),
                    "risk_prediction": prediction.model_dump(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await manager.broadcast(payload)
        except Exception:
            pass
        await asyncio.sleep(interval_seconds)


# --- Router Definition ---
router = APIRouter(tags=["Rockfall Telemetry & Prediction"])


@router.post(
    "/predict",
    response_model=RiskPrediction,
    status_code=status.HTTP_200_OK,
    summary="Mock Rockfall Risk Inference Endpoint",
    description="Returns random-but-plausible RiskPrediction weighted 60% Safe / 25% Warning / 15% Evacuation."
)
async def predict_rockfall(
    reading: Optional[SensorReading] = Body(default=None)
) -> RiskPrediction:
    zone_id = reading.zone_id if reading else None
    prediction, _ = generate_mock_reading_and_prediction(zone_id=zone_id)
    return prediction


@router.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket) -> None:
    """WebSocket feed broadcasting SensorReading + RiskPrediction every few seconds."""
    await manager.connect(websocket)
    # Send immediate initial state
    try:
        prediction, reading = generate_mock_reading_and_prediction()
        await websocket.send_text(json.dumps({
            "type": "telemetry_update",
            "sensor_reading": reading.model_dump(),
            "risk_prediction": prediction.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
    except Exception:
        pass

    try:
        while True:
            # Keep-alive receive loop
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket)
