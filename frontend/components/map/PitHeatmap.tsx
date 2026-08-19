'use client';

import React, { useMemo } from 'react';
import Map, { Source, Layer, NavigationControl } from 'react-map-gl/maplibre';
import type { LayerProps } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { PitZoneRisk } from '@/types';

interface PitHeatmapProps {
  zones?: PitZoneRisk[];
  center?: { longitude: number; latitude: number };
  zoom?: number;
}

const defaultZones: PitZoneRisk[] = [
  { zoneId: 'Z-01', name: 'North Highwall', latitude: 23.7957, longitude: 86.4304, riskScore: 0.85, riskLevel: 'Evacuation', activeSensors: 8, lastUpdated: new Date().toISOString() },
  { zoneId: 'Z-02', name: 'East Haul Road', latitude: 23.7920, longitude: 86.4350, riskScore: 0.55, riskLevel: 'Warning', activeSensors: 5, lastUpdated: new Date().toISOString() },
  { zoneId: 'Z-03', name: 'South Slope Bench', latitude: 23.7880, longitude: 86.4290, riskScore: 0.15, riskLevel: 'Safe', activeSensors: 6, lastUpdated: new Date().toISOString() },
  { zoneId: 'Z-04', name: 'West Pit Crest', latitude: 23.7910, longitude: 86.4220, riskScore: 0.20, riskLevel: 'Safe', activeSensors: 4, lastUpdated: new Date().toISOString() },
];

export default function PitHeatmap({
  zones = defaultZones,
  center = { longitude: 86.4304, latitude: 23.7920 },
  zoom = 14,
}: PitHeatmapProps) {
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
        color: zone.riskLevel === 'Evacuation' ? '#ef4444' : zone.riskLevel === 'Warning' ? '#f59e0b' : '#10b981',
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
        mapStyle="https://demotiles.maplibre.org/style.json"
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
