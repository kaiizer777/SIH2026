'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';

// Dynamically import PitHeatmap since MapLibre uses browser window/canvas
const PitHeatmap = dynamic(() => import('@/components/map/PitHeatmap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[500px] flex items-center justify-center bg-slate-900/50 rounded-xl border border-slate-800 animate-pulse text-slate-400">
      Loading Open-Pit 3D Heatmap...
    </div>
  ),
});

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-emerald-400 text-xs font-mono tracking-wide uppercase">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            SIH25071 • Live Pit Monitoring
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight mt-1 text-slate-50">
            Open-Pit Spatial Risk Dashboard
          </h1>
          <p className="text-slate-400 text-sm mt-0.5">
            Geotechnical radar & multi-sensor slope stability analysis
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/alerts"
            className="px-4 py-2 text-sm font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            View Alerts
          </Link>
          <Link
            href="/trends"
            className="px-4 py-2 text-sm font-medium rounded-lg bg-sky-600 hover:bg-sky-500 text-white transition shadow-lg shadow-sky-900/30"
          >
            Telemetry Trends →
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Active Sensors</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">24 / 24</div>
          <div className="text-xs text-emerald-400 mt-1">100% Operational</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Critical Sectors</div>
          <div className="text-2xl font-bold text-rose-400 mt-1">1 Zone</div>
          <div className="text-xs text-rose-400/80 mt-1">North Highwall (Evacuation)</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Max Velocity</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">1.80 mm/day</div>
          <div className="text-xs text-amber-400/80 mt-1">Accelerating (Inverse-Vel model)</div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Model Confidence</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">94.8%</div>
          <div className="text-xs text-sky-400/80 mt-1">Ensemble (GRU + XGBoost)</div>
        </div>
      </div>

      {/* Main Heatmap Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-200">Pit Spatial Heatmap</h2>
          <span className="text-xs font-mono text-slate-400">MapLibre Engine • WebGL</span>
        </div>
        <PitHeatmap />
      </div>
    </div>
  );
}
