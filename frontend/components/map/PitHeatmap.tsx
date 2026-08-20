'use client';

import React, { useMemo, useEffect, useState } from 'react';
import Map, { Source, Layer, NavigationControl } from 'react-map-gl/maplibre';
import type { LayerProps } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { SensorWebSocketClient } from '@/lib/websocket';
import { RiskLevel, WebSocketMessage } from '@/lib/types';

interface PitZoneRisk {
  zoneId: string;
  name: string;
  latitude: number;
  longitude: number;
  riskScore: number;
  riskLevel: RiskLevel;
  activeSensors: number;
  lastUpdated: string;
}

interface PitHeatmapProps {
  center?: { longitude: number; latitude: number };
  zoom?: number;
}

// Generate static coordinates for the 16 pit zones
const ZONE_COORDS: Record<string, { lat: number, lon: number, name: string }> = {
  'zone_01': { lat: 23.7957, lon: 86.4304, name: 'North Highwall (Z1)' },
  'zone_02': { lat: 23.7920, lon: 86.4350, name: 'East Haul Road (Z2)' },
  'zone_03': { lat: 23.7880, lon: 86.4290, name: 'South Slope Bench (Z3)' },
  'zone_04': { lat: 23.7910, lon: 86.4220, name: 'West Pit Crest (Z4)' },
};
for (let i = 5; i <= 16; i++) {
  const row = Math.floor((i - 1) / 4);
  const col = (i - 1) % 4;
  const zoneStr = `zone_${i.toString().padStart(2, '0')}`;
  ZONE_COORDS[zoneStr] = {
    lat: 23.7957 - (row * 0.003),
    lon: 86.4220 + (col * 0.004),
    name: `Sector ${i}`
  };
}

const localMapStyle = {
  version: 8 as const,
  sources: {},
  layers: [
    {
      id: 'background',
      type: 'background' as const,
      paint: {
        'background-color': '#0b0f19', // Matches the slate-950 background
      },
    },
  ],
};

export default function PitHeatmap({
  center = { longitude: 86.4304, latitude: 23.7920 },
  zoom = 14,
}: PitHeatmapProps) {
  const [zonesMap, setZonesMap] = useState<Record<string, PitZoneRisk>>({});

  useEffect(() => {
    const wsClient = new SensorWebSocketClient();
    
    const unsubscribe = wsClient.onMessage((msg: WebSocketMessage) => {
      console.log(`[HEATMAP_WS] Received message type: ${msg.type}`);
      if (msg.type === 'telemetry_update') {
        const { sensor_reading, risk_prediction, timestamp } = msg;
        const zid = sensor_reading.zone_id;
        const coords = ZONE_COORDS[zid] || { lat: center.latitude, lon: center.longitude, name: zid };
        
        console.log(`[HEATMAP_WS] Telemetry update for zone: ${zid}, risk: ${risk_prediction.risk_level}`);
        
        setZonesMap((prev) => ({
          ...prev,
          [zid]: {
            zoneId: zid,
            name: coords.name,
            latitude: coords.lat,
            longitude: coords.lon,
            riskScore: risk_prediction.risk_score,
            riskLevel: risk_prediction.risk_level,
            activeSensors: 1, // backend has 1 sensor per zone in this sim
            lastUpdated: timestamp,
          }
        }));
      }
    });

    wsClient.connect();
    return () => {
      unsubscribe();
      wsClient.disconnect();
    };
  }, [center.latitude, center.longitude]);

  const zones = Object.values(zonesMap);

  const geojson = useMemo(() => ({
    type: 'FeatureCollection' as const,
    features: zones.map((zone) => ({
      type: 'Feature' as const,
      geometry: {
        type: 'Point' as const,
        coordinates: [zone.longitude, zone.latitude],
      },
      properties: {
        id: zone.zoneId,
        name: zone.name,
        riskScore: zone.riskScore,
        riskLevel: zone.riskLevel,
        color: zone.riskLevel === 'evacuation' ? '#ef4444' : zone.riskLevel === 'warning' ? '#f59e0b' : '#10b981',
      },
    })),
  }), [zones]);

  const circleLayer: LayerProps = {
    id: 'risk-circles',
    type: 'circle',
    paint: {
      'circle-radius': 24,
      'circle-color': ['get', 'color'],
      'circle-opacity': 0.75,
      'circle-stroke-width': 2,
      'circle-stroke-color': '#ffffff',
      'circle-blur': 0.2,
    },
  };

  return (
    <div className="relative w-full h-[500px] rounded-xl overflow-hidden border border-slate-700/60 shadow-2xl bg-slate-950">
      <Map
        initialViewState={{
          longitude: center.longitude,
          latitude: center.latitude,
          zoom: zoom,
        }}
        style={{ width: '100%', height: '100%' }}
        mapStyle={localMapStyle}
      >
        <NavigationControl position="top-right" />
        <Source id="zones-data" type="geojson" data={geojson}>
          <Layer {...circleLayer} />
        </Source>
      </Map>

      {/* Legend Overlay */}
      <div className="absolute bottom-4 left-4 bg-slate-900/90 backdrop-blur-md border border-slate-700/50 p-3 rounded-lg text-xs space-y-2 text-slate-200">
        <div className="font-semibold text-slate-100 mb-1">Open-Pit Stability Heatmap</div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" />
          <span>Safe (&lt; 0.3)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-amber-500 inline-block" />
          <span>Warning (0.3 - 0.7)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500 inline-block" />
          <span>Evacuation (&gt; 0.7)</span>
        </div>
      </div>
    </div>
  );
}
