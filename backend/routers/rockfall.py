from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field


# --- Enums & Data Schemas ---
class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SlopeSensorData(BaseModel):
    sensor_id: str = Field(..., example="SNS-MINE-042", description="Unique sensor tag")
    tilt_angle_degrees: float = Field(..., ge=-90.0, le=90.0, example=14.2)
    displacement_mm: float = Field(..., ge=0.0, example=3.7)
    pore_pressure_kpa: float = Field(..., ge=0.0, example=120.5)
    seismic_vibration_g: float = Field(..., ge=0.0, example=0.04)


class PredictionResponse(BaseModel):
    zone_id: str
    risk_level: RiskLevel
    rockfall_probability: float = Field(..., ge=0.0, le=1.0)
    recommended_action: str
    evaluated_at: str


class AlertNotificationRequest(BaseModel):
    zone_id: str = Field(..., example="PIT-NORTH-ZONE-B")
    risk_level: RiskLevel = Field(default=RiskLevel.HIGH)
    operator_notes: Optional[str] = Field(None, max_length=200, example="Triggering siren for North bench evacuation")


class AlertNotificationResponse(BaseModel):
    alert_id: str
    zone_id: str
    status: str
    broadcast_time: str


# --- Router Initialization ---
router = APIRouter(
    prefix="/api/rockfall",
    tags=["Rockfall & Sensor Analytics"]
)


# --- Route Handlers ---
@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Slope Stability & Rockfall Probability"
)
async def predict_rockfall_risk(data: SlopeSensorData) -> PredictionResponse:
    """
    Receives real-time telemetry from geotech sensors and calculates
    rockfall probability and hazard level.
    """
    # Deterministic risk evaluation logic
    score = (
        (data.displacement_mm * 0.15) +
        (abs(data.tilt_angle_degrees) * 0.03) +
        (data.seismic_vibration_g * 4.0) +
        (data.pore_pressure_kpa * 0.002)
    )
    probability = min(max(round(score / 5.0, 3), 0.0), 1.0)

    if probability > 0.75:
        risk = RiskLevel.CRITICAL
        action = "Evacuate sector immediately and sound primary siren."
    elif probability > 0.50:
        risk = RiskLevel.HIGH
        action = "Halt excavation vehicles and deploy geotechnical inspection squad."
    elif probability > 0.25:
        risk = RiskLevel.MEDIUM
        action = "Increase sensor telemetry poll rate to 500ms."
    else:
        risk = RiskLevel.LOW
        action = "Normal operational parameters. Slope stable."

    return PredictionResponse(
        zone_id="BENCH-WEST-01",
        risk_level=risk,
        rockfall_probability=probability,
        recommended_action=action,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/zones/{zone_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get Specific Pit Zone Telemetry Status"
)
async def get_zone_status(
    zone_id: str,
    include_history: bool = Query(False, description="Include past 24h trend data")
):
    if zone_id.upper() not in ["ZONE-A", "ZONE-B", "ZONE-C", "PIT-NORTH"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pit Zone '{zone_id}' not found in mine registry."
        )

    response = {
        "zone_id": zone_id.upper(),
        "status": "MONITORED",
        "active_sensors": 12,
        "last_ping_utc": datetime.now(timezone.utc).isoformat(),
    }
    if include_history:
        response["displacement_history_mm"] = [1.2, 1.4, 1.9, 2.3, 3.1]

    return response


@router.post(
    "/alert",
    response_model=AlertNotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch Emergency Evacuation Alert"
)
async def trigger_emergency_alert(payload: AlertNotificationRequest) -> AlertNotificationResponse:
    return AlertNotificationResponse(
        alert_id=f"ALT-{int(datetime.now(timezone.utc).timestamp())}",
        zone_id=payload.zone_id,
        status="DISPATCHED",
        broadcast_time=datetime.now(timezone.utc).isoformat()
    )
