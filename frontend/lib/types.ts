/**
 * SIH25071 Rockfall Prediction - Core Data Contract Types
 * Hand-mirrored from backend/app/schemas.py for zero-translation-risk.
 * Field names, casing (snake_case), and shapes match schemas.py exactly.
 */

export type RiskLevel = 'safe' | 'warning' | 'evacuation';

export interface SensorReading {
  sensor_id: string;
  zone_id: string;
  timestamp: string;
  displacement_mm_day: number;
  vibration: number;
  pore_pressure: number;
  strain: number;
  rainfall_mm: number;
  risk_level?: RiskLevel | null;
}

export interface RiskPrediction {
  zone_id: string;
  timestamp: string;
  risk_level: RiskLevel;
  risk_score: number;
  displacement_velocity_mm_day: number;
  model_version: string;
}

export type AlertSeverity = 'advisory' | 'warning' | 'evacuation' | 'safe';

export interface AlertEvent {
  alert_id: string;
  zone_id: string;
  severity: AlertSeverity | string;
  message: string;
  triggered_at: string;
  acknowledged: boolean;
}

export interface TelemetryUpdateMessage {
  type: 'telemetry_update';
  sensor_reading: SensorReading;
  risk_prediction: RiskPrediction;
  timestamp: string;
}

export interface AlertEventMessage {
  type: 'alert_event';
  alert: AlertEvent;
  timestamp: string;
}

export type WebSocketMessage = TelemetryUpdateMessage | AlertEventMessage;

/**
 * Grounded Displacement Velocity Thresholds (mm/day)
 * Safe: 0–50 mm/day, Warning: 50–120 mm/day, Evacuation: >120 mm/day
 */
export const SAFE_DISPLACEMENT_MAX_MM_DAY = 50.0;
export const WARNING_DISPLACEMENT_MIN_MM_DAY = 50.0;
export const WARNING_DISPLACEMENT_MAX_MM_DAY = 120.0;
export const EVACUATION_DISPLACEMENT_MIN_MM_DAY = 120.0;
