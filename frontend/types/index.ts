export type RiskLevel = 'Safe' | 'Warning' | 'Evacuation';

export interface SensorReading {
  sensorId: string;
  pitZone: string;
  timestamp: string;
  displacementMm: number;
  velocityMmPerDay: number;
  porePressureKPa: number;
  seismicMagnitude?: number;
  temperatureCelsius?: number;
  batteryLevelPct?: number;
}

export interface Alert {
  id: string;
  timestamp: string;
  level: RiskLevel;
  zone: string;
  sensorId?: string;
  message: string;
  probability: number;
  status: 'active' | 'acknowledged' | 'resolved';
}

export interface PitZoneRisk {
  zoneId: string;
  name: string;
  latitude: number;
  longitude: number;
  riskScore: number; // 0 to 1
  riskLevel: RiskLevel;
  activeSensors: number;
  lastUpdated: string;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'critical';
  backendVersion: string;
  activeSensorsCount: number;
  activeAlertsCount: number;
  uptimeSeconds: number;
}
