from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# --- Risk Level Enum ---
class RiskLevel(str, Enum):
    SAFE = "safe"
    WARNING = "warning"
    EVACUATION = "evacuation"


# --- Grounded Displacement Velocity Thresholds (mm/day) ---
# Derived from real open-pit Slope Stability Radar (SSR) case study:
# Safe: 0–50 mm/day
# Warning: 50–120 mm/day
# Evacuation: >120 mm/day
SAFE_DISPLACEMENT_MAX_MM_DAY: float = 50.0
WARNING_DISPLACEMENT_MIN_MM_DAY: float = 50.0
WARNING_DISPLACEMENT_MAX_MM_DAY: float = 120.0
EVACUATION_DISPLACEMENT_MIN_MM_DAY: float = 120.0


# --- Data Contract Schemas ---
class SensorReading(BaseModel):
    sensor_id: str
    zone_id: str
    timestamp: str
    displacement_mm_day: float
    vibration: float
    pore_pressure: float
    strain: float
    rainfall_mm: float
    risk_level: Optional[RiskLevel] = None


class RiskPrediction(BaseModel):
    zone_id: str
    timestamp: str
    risk_level: RiskLevel
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk probability score (0-1)")
    displacement_velocity_mm_day: float
    model_version: str


class AlertEvent(BaseModel):
    alert_id: str
    zone_id: str
    severity: str
    message: str
    triggered_at: str
    acknowledged: bool
