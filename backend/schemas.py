"""Re-export schemas for top-level import convenience."""
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

__all__ = [
    "RiskLevel",
    "SensorReading",
    "RiskPrediction",
    "AlertEvent",
    "SAFE_DISPLACEMENT_MAX_MM_DAY",
    "WARNING_DISPLACEMENT_MIN_MM_DAY",
    "WARNING_DISPLACEMENT_MAX_MM_DAY",
    "EVACUATION_DISPLACEMENT_MIN_MM_DAY",
]
