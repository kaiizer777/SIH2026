'use client';

import React, { useMemo, useEffect, useState, useCallback } from 'react';
import Map, { Source, Layer, NavigationControl, Popup } from 'react-map-gl/maplibre';
import type { LayerProps, MapLayerMouseEvent } from 'react-map-gl/maplibre';
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
const ZONE_COORDS: Record<string, { lat: number; lon: number; name: string }> = {
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
    lat: 23.7957 - row * 0.003,
    lon: 86.4220 + col * 0.004,
    name: `Sector ${i}`,
  };
}

// Pre-populate realistic initial baseline data so the map is never a blank void
const INITIAL_ZONES: Record<string, PitZoneRisk> = {};
const BASELINE_PRESETS: Record<string, { score: number; level: RiskLevel }> = {
  'zone_01': { score: 0.88, level: 'evacuation' },
  'zone_02': { score: 0.58, level: 'warning' },
  'zone_03': { score: 0.12, level: 'safe' },
  'zone_04': { score: 0.08, level: 'safe' },
};

Object.entries(ZONE_COORDS).forEach(([zid, coords]) => {
  const preset = BASELINE_PRESETS[zid] || {
    score: Math.round((0.06 + ((parseInt(zid.split('_')[1], 10) * 7) % 18) * 0.01) * 100) / 100,
    level: 'safe' as RiskLevel,
  };
  INITIAL_ZONES[zid] = {
    zoneId: zid,
    name: coords.name,
    latitude: coords.lat,
    longitude: coords.lon,
    riskScore: preset.score,
    riskLevel: preset.level,
    activeSensors: 1,
    lastUpdated: 'Baseline Ready',
  };
});

function generatePitTopographyGeoJSON(centerLat = 23.7920, centerLon = 86.4304) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const features: any[] = [];

  // 1. Pit Bench Polygons (from Outer Crest to Pit Floor)
  const benchLevels = [
    { name: 'Mine Surface Boundary', rX: 0.0125, rY: 0.0095, fill: '#f1f5f9', stroke: '#cbd5e1', label: 'EL +280m' },
    { name: 'Pit Crest Outer Bench', rX: 0.0095, rY: 0.0075, fill: '#e2e8f0', stroke: '#94a3b8', label: 'Bench 1 (EL +220m)' },
    { name: 'Upper Highwall Bench', rX: 0.0075, rY: 0.0058, fill: '#cbd5e1', stroke: '#64748b', label: 'Bench 2 (EL +160m)' },
    { name: 'Mid-Slope Bench', rX: 0.0055, rY: 0.0042, fill: '#b0bccb', stroke: '#475569', label: 'Bench 3 (EL +100m)' },
    { name: 'Lower Haul Bench', rX: 0.0035, rY: 0.0028, fill: '#94a3b8', stroke: '#334155', label: 'Bench 4 (EL +40m)' },
    { name: 'Pit Sump Floor', rX: 0.0018, rY: 0.0014, fill: '#64748b', stroke: '#1e293b', label: 'Floor (EL -20m)' },
  ];

  benchLevels.forEach((bench, idx) => {
    const points: [number, number][] = [];
    const numPoints = 64;
    for (let i = 0; i <= numPoints; i++) {
      const angle = (i / numPoints) * 2 * Math.PI;
      const wobble = 1 + 0.04 * Math.sin(angle * 3) + 0.02 * Math.cos(angle * 5);
      const lon = centerLon + bench.rX * Math.cos(angle) * wobble;
      const lat = centerLat + bench.rY * Math.sin(angle) * wobble;
      points.push([lon, lat]);
    }
    features.push({
      type: 'Feature',
      geometry: { type: 'Polygon', coordinates: [points] },
      properties: {
        type: 'bench',
        level: idx,
        name: bench.name,
        fill: bench.fill,
        stroke: bench.stroke,
        label: bench.label,
      },
    });
  });

  // 2. Haul Roads (Main Spiral Ramp)
  const haulRoadPoints: [number, number][] = [];
  const rampSteps = 80;
  for (let i = 0; i <= rampSteps; i++) {
    const t = i / rampSteps;
    const angle = t * 3.5 * Math.PI;
    const rX = 0.0095 * (1 - 0.75 * t);
    const rY = 0.0075 * (1 - 0.75 * t);
    const lon = centerLon + rX * Math.cos(angle);
    const lat = centerLat + rY * Math.sin(angle);
    haulRoadPoints.push([lon, lat]);
  }
  features.push({
    type: 'Feature',
    geometry: { type: 'LineString', coordinates: haulRoadPoints },
    properties: { type: 'haul_road', name: 'Primary Haul Ramp' },
  });

  // 3. Highwall Hazard Line (North Edge)
  const highwallLine: [number, number][] = [];
  for (let i = 0; i <= 20; i++) {
    const t = i / 20;
    const lon = centerLon - 0.008 + t * 0.016;
    const lat = centerLat + 0.0055 + 0.0006 * Math.sin(t * Math.PI);
    highwallLine.push([lon, lat]);
  }
  features.push({
    type: 'Feature',
    geometry: { type: 'LineString', coordinates: highwallLine },
    properties: { type: 'highwall', name: 'North Highwall Crest Escarpment' },
  });

  // 4. Survey Grid Lines
  for (let dLon = -0.012; dLon <= 0.012; dLon += 0.006) {
    features.push({
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [
          [centerLon + dLon, centerLat - 0.010],
          [centerLon + dLon, centerLat + 0.010],
        ],
      },
      properties: { type: 'grid' },
    });
  }
  for (let dLat = -0.008; dLat <= 0.008; dLat += 0.004) {
    features.push({
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [
          [centerLon - 0.014, centerLat + dLat],
          [centerLon + 0.014, centerLat + dLat],
        ],
      },
      properties: { type: 'grid' },
    });
  }

  return {
    type: 'FeatureCollection' as const,
    features,
  };
}

export default function PitHeatmap({
  center = { longitude: 86.4304, latitude: 23.7920 },
  zoom = 14.5,
}: PitHeatmapProps) {
  const [zonesMap, setZonesMap] = useState<Record<string, PitZoneRisk>>(INITIAL_ZONES);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'open' | 'closed' | 'error'>('connecting');
  const [selectedZone, setSelectedZone] = useState<PitZoneRisk | null>(null);
  const [cursor, setCursor] = useState<string>('auto');
  const [workerReady, setWorkerReady] = useState<boolean>(false);

  useEffect(() => {
    // Dynamic import of maplibre-gl to call setWorkerUrl. This pins the
    // worker URL to our /public copy so the browser doesn't try to resolve
    // import.meta.url inside node_modules (which 404s).
    //
    // The build must use the webpack bundler (see next.config.ts) — Turbopack
    // build cannot analyze maplibre-gl's `new URL(e, import.meta.url)` Blob
    // fallback. Dev mode (Turbopack) is more lenient and works fine.
    import('maplibre-gl')
      .then(({ setWorkerUrl }) => {
        setWorkerUrl('/maplibre-gl-worker.mjs');
      })
      .catch((err) => {
        // If the dynamic import fails for any reason, still unblock the Map
        // render so the UI doesn't stay blank. The map will fall back to its
        // default worker URL.
        console.error('[PitHeatmap] Failed to configure maplibre worker URL:', err);
      })
      .finally(() => {
        setWorkerReady(true);
      });
  }, []);

  useEffect(() => {
    const wsClient = new SensorWebSocketClient();

    wsClient.onStatusChange((status) => {
      setWsStatus(status);
    });
    
    const unsubscribe = wsClient.onMessage((msg: WebSocketMessage) => {
      if (msg.type === 'telemetry_update') {
        const { sensor_reading, risk_prediction, timestamp } = msg;
        const zid = sensor_reading.zone_id;
        const coords = ZONE_COORDS[zid] || { lat: center.latitude, lon: center.longitude, name: zid };
        
        setZonesMap((prev) => ({
          ...prev,
          [zid]: {
            zoneId: zid,
            name: coords.name,
            latitude: coords.lat,
            longitude: coords.lon,
            riskScore: risk_prediction.risk_score,
            riskLevel: risk_prediction.risk_level,
            activeSensors: 1,
            lastUpdated: new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          },
        }));
      }
    });

    wsClient.connect();
    return () => {
      unsubscribe();
      wsClient.disconnect();
    };
  }, [center.latitude, center.longitude]);

  const topographyGeoJson = useMemo(() => generatePitTopographyGeoJSON(center.latitude, center.longitude), [center.latitude, center.longitude]);
  const zones = useMemo(() => Object.values(zonesMap), [zonesMap]);

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
        color:
          zone.riskLevel === 'evacuation'
            ? '#ef4444'
            : zone.riskLevel === 'warning'
            ? '#f59e0b'
            : '#10b981',
      },
    })),
  }), [zones]);

  // Topography Layers
  const benchFillLayer: LayerProps = {
    id: 'pit-bench-fills',
    type: 'fill',
    filter: ['==', ['get', 'type'], 'bench'],
    paint: {
      'fill-color': ['get', 'fill'],
      'fill-opacity': 0.85,
    },
  };

  const benchLineLayer: LayerProps = {
    id: 'pit-bench-lines',
    type: 'line',
    filter: ['==', ['get', 'type'], 'bench'],
    paint: {
      'line-color': ['get', 'stroke'],
      'line-width': 1.5,
      'line-opacity': 0.9,
    },
  };

  const gridLineLayer: LayerProps = {
    id: 'pit-grid-lines',
    type: 'line',
    filter: ['==', ['get', 'type'], 'grid'],
    paint: {
      'line-color': '#94a3b8',
      'line-width': 0.75,
      'line-opacity': 0.35,
      'line-dasharray': [3, 3],
    },
  };

  const haulRoadCasingLayer: LayerProps = {
    id: 'pit-haul-road-casing',
    type: 'line',
    filter: ['==', ['get', 'type'], 'haul_road'],
    paint: {
      'line-color': '#1e293b',
      'line-width': 6,
      'line-opacity': 0.3,
    },
  };

  const haulRoadLayer: LayerProps = {
    id: 'pit-haul-road',
    type: 'line',
    filter: ['==', ['get', 'type'], 'haul_road'],
    paint: {
      'line-color': '#f59e0b',
      'line-width': 3,
      'line-opacity': 0.95,
    },
  };

  const highwallLayer: LayerProps = {
    id: 'pit-highwall-line',
    type: 'line',
    filter: ['==', ['get', 'type'], 'highwall'],
    paint: {
      'line-color': '#ef4444',
      'line-width': 2.5,
      'line-dasharray': [2, 2],
      'line-opacity': 0.85,
    },
  };

  // Sensor Telemetry Layers
  const glowLayer: LayerProps = {
    id: 'risk-glow',
    type: 'circle',
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        12, 20,
        14, 34,
        16, 52,
      ],
      'circle-color': ['get', 'color'],
      'circle-opacity': 0.35,
      'circle-blur': 0.65,
    },
  };

  const circleLayer: LayerProps = {
    id: 'risk-circles',
    type: 'circle',
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        12, 10,
        14, 15,
        16, 22,
      ],
      'circle-color': ['get', 'color'],
      'circle-opacity': 0.95,
      'circle-stroke-width': 2.5,
      'circle-stroke-color': '#ffffff',
    },
  };

  const centerDotLayer: LayerProps = {
    id: 'risk-center-dot',
    type: 'circle',
    paint: {
      'circle-radius': 4,
      'circle-color': '#ffffff',
    },
  };

  const onMouseEnter = useCallback(() => setCursor('pointer'), []);
  const onMouseLeave = useCallback(() => setCursor('auto'), []);

  const onClick = useCallback((event: MapLayerMouseEvent) => {
    const feature = event.features && event.features[0];
    if (feature && feature.properties) {
      const zoneId = feature.properties.id;
      const zone = zonesMap[zoneId];
      if (zone) {
        setSelectedZone(zone);
      }
    }
  }, [zonesMap]);

  return (
    <div className="relative w-full h-[520px] rounded-2xl overflow-hidden border border-[#E6E8EE] bg-[#F8FAFC] shadow-sm">
      {workerReady && (
      <Map
        initialViewState={{
          longitude: center.longitude,
          latitude: center.latitude,
          zoom: zoom,
        }}
        cursor={cursor}
        interactiveLayerIds={['risk-circles', 'risk-glow']}
        onClick={onClick}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        style={{ width: '100%', height: '100%' }}
        mapStyle="/style.json"
      >
        <NavigationControl position="top-right" />

        {/* 1. Open-Pit Bench Topography, Haul Roads, and Survey Grid */}
        <Source id="pit-topography" type="geojson" data={topographyGeoJson}>
          <Layer {...benchFillLayer} />
          <Layer {...benchLineLayer} />
          <Layer {...gridLineLayer} />
          <Layer {...haulRoadCasingLayer} />
          <Layer {...haulRoadLayer} />
          <Layer {...highwallLayer} />
        </Source>

        {/* 2. Geotechnical Risk Sensor Nodes */}
        <Source id="zones-data" type="geojson" data={geojson}>
          <Layer {...glowLayer} />
          <Layer {...circleLayer} />
          <Layer {...centerDotLayer} />
        </Source>

        {selectedZone && (
          <Popup
            longitude={selectedZone.longitude}
            latitude={selectedZone.latitude}
            anchor="bottom"
            offset={24}
            onClose={() => setSelectedZone(null)}
            closeButton={true}
            closeOnClick={false}
            className="z-50"
          >
            <div className="p-2 min-w-[200px] text-[#0B1220] font-sans">
              <div className="flex items-center justify-between gap-2 border-b border-[#E6E8EE] pb-1.5 mb-2">
                <span className="font-semibold text-xs text-[#0B1220]">{selectedZone.name}</span>
                <span
                  className={`text-[9px] font-mono font-semibold uppercase px-1.5 py-0.5 rounded ${
                    selectedZone.riskLevel === 'evacuation'
                      ? 'bg-rose-100 text-rose-700'
                      : selectedZone.riskLevel === 'warning'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-emerald-100 text-emerald-700'
                  }`}
                >
                  {selectedZone.riskLevel}
                </span>
              </div>
              <div className="text-[11px] space-y-1 text-[#5B6472]">
                <div className="flex justify-between">
                  <span>Risk Score:</span>
                  <span className="font-mono font-semibold text-[#0B1220]">{selectedZone.riskScore}</span>
                </div>
                <div className="flex justify-between">
                  <span>Coordinates:</span>
                  <span className="font-mono text-[10px] text-[#0B1220]">
                    {selectedZone.latitude.toFixed(4)}, {selectedZone.longitude.toFixed(4)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Telemetry:</span>
                  <span className="text-[#0B1220] font-medium">{selectedZone.lastUpdated}</span>
                </div>
              </div>
            </div>
          </Popup>
        )}
      </Map>
      )}

      {/* Top Left Feed Status Badge */}
      <div className="absolute top-4 left-4 flex items-center gap-2 bg-white/95 backdrop-blur-md border border-[#E6E8EE] px-3 py-1.5 rounded-full text-xs font-mono shadow-sm">
        <span
          className={`w-2 h-2 rounded-full ${
            wsStatus === 'open'
              ? 'bg-emerald-500 animate-pulse'
              : wsStatus === 'connecting'
              ? 'bg-amber-500 animate-pulse'
              : 'bg-slate-400'
          }`}
        />
        <span className="text-[11px] text-[#0B1220] font-medium">
          {wsStatus === 'open'
            ? 'Live WebSocket Feed'
            : wsStatus === 'connecting'
            ? 'Connecting Sensor Feed...'
            : 'Physics Baseline Telemetry'}
        </span>
      </div>

      {/* Legend Overlay */}
      <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-md border border-[#E6E8EE] p-3.5 rounded-xl text-xs space-y-2 text-[#0B1220] shadow-lg shadow-slate-900/5">
        <div className="font-semibold text-[#0B1220] text-[12px]">Open-Pit Stability Heatmap</div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
          <span className="text-[#5B6472]">Safe (&lt; 0.3)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
          <span className="text-[#5B6472]">Warning (0.3 - 0.7)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-600 inline-block" />
          <span className="text-[#5B6472]">Evacuation (&gt; 0.7)</span>
        </div>
        <div className="pt-1.5 border-t border-[#E6E8EE] flex items-center gap-3 text-[10px] text-[#8A93A1]">
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-amber-500 inline-block" /> Haul Road
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-0.5 border-t border-dashed border-rose-500 inline-block" /> Highwall
          </span>
        </div>
      </div>
    </div>
  );
}


