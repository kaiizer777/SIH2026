import React from 'react';
import Link from 'next/link';
import { TrendChart } from '@/components/charts';

export default function TrendsPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-sky-400 text-xs font-mono tracking-wide uppercase">
            <span className="w-2 h-2 rounded-full bg-sky-400 animate-pulse" />
            Time-Series Analytics
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight mt-1 text-slate-50">
            Geotechnical Telemetry & Trend Analysis
          </h1>
          <p className="text-slate-400 text-sm mt-0.5">
            Real-time multi-parameter sensor feeds (Displacement, Velocity, Pore Pressure)
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="px-4 py-2 text-sm font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            ← Back to Map
          </Link>
          <Link
            href="/alerts"
            className="px-4 py-2 text-sm font-medium rounded-lg bg-rose-600/90 hover:bg-rose-600 text-white transition shadow-lg shadow-rose-900/30"
          >
            Alert Log
          </Link>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 gap-6">
        <TrendChart
          title="North Highwall Sector (Critical Failure Risk Area)"
          zoneId="zone_01"
          data={[
            { time: '08:00', displacement: 1.2, velocity: 0.08, porePressure: 38 },
            { time: '10:00', displacement: 1.6, velocity: 0.11, porePressure: 42 },
            { time: '12:00', displacement: 2.1, velocity: 0.18, porePressure: 49 },
            { time: '14:00', displacement: 3.4, velocity: 0.45, porePressure: 64 },
            { time: '16:00', displacement: 5.8, velocity: 0.98, porePressure: 88 },
            { time: '18:00', displacement: 8.5, velocity: 1.85, porePressure: 112 },
          ]}
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TrendChart
            title="East Haul Road (Haulage Safety Corridor)"
            zoneId="zone_02"
            data={[
              { time: '08:00', displacement: 0.5, velocity: 0.02, porePressure: 22 },
              { time: '10:00', displacement: 0.6, velocity: 0.03, porePressure: 24 },
              { time: '12:00', displacement: 0.8, velocity: 0.05, porePressure: 28 },
              { time: '14:00', displacement: 1.1, velocity: 0.09, porePressure: 35 },
              { time: '16:00', displacement: 1.3, velocity: 0.10, porePressure: 37 },
              { time: '18:00', displacement: 1.5, velocity: 0.12, porePressure: 40 },
            ]}
          />

          <TrendChart
            title="South Slope Crest (Baseline Stability)"
            zoneId="zone_03"
            data={[
              { time: '08:00', displacement: 0.2, velocity: 0.01, porePressure: 15 },
              { time: '10:00', displacement: 0.2, velocity: 0.01, porePressure: 15 },
              { time: '12:00', displacement: 0.25, velocity: 0.01, porePressure: 16 },
              { time: '14:00', displacement: 0.3, velocity: 0.02, porePressure: 17 },
              { time: '16:00', displacement: 0.3, velocity: 0.01, porePressure: 17 },
              { time: '18:00', displacement: 0.35, velocity: 0.02, porePressure: 18 },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
