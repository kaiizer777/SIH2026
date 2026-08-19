import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6 md:p-12 relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-4xl w-full text-center space-y-8 z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-slate-300 text-xs font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          SIH25071 • Geotechnical AI Surveillance
        </div>

        <div className="space-y-4">
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight bg-gradient-to-r from-slate-100 via-sky-200 to-slate-400 bg-clip-text text-transparent">
            AI-Based Rockfall Prediction & Alert System
          </h1>
          <p className="text-slate-400 text-base md:text-lg max-w-2xl mx-auto leading-relaxed">
            Real-time radar telemetry, inverse-velocity displacement modeling, and spatial open-pit risk heatmaps for smart mine safety.
          </p>
        </div>

        {/* Quick Launch Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-left pt-4">
          <Link
            href="/dashboard"
            className="group p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-sky-500/50 transition duration-300 hover:shadow-xl hover:shadow-sky-500/5"
          >
            <div className="text-sky-400 text-2xl mb-3">🗺️</div>
            <h2 className="text-lg font-semibold text-slate-100 group-hover:text-sky-300 transition">
              Pit Heatmap
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              Interactive 3D spatial map of open-pit benches with zone-level risk scoring.
            </p>
            <span className="inline-block mt-4 text-xs font-mono text-sky-400 group-hover:translate-x-1 transition">
              Launch Dashboard →
            </span>
          </Link>

          <Link
            href="/alerts"
            className="group p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-rose-500/50 transition duration-300 hover:shadow-xl hover:shadow-rose-500/5"
          >
            <div className="text-rose-400 text-2xl mb-3">🚨</div>
            <h2 className="text-lg font-semibold text-slate-100 group-hover:text-rose-300 transition">
              Alert Log
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              Automated warning dispatch, siren status, and geotech incident response logs.
            </p>
            <span className="inline-block mt-4 text-xs font-mono text-rose-400 group-hover:translate-x-1 transition">
              Review Alerts →
            </span>
          </Link>

          <Link
            href="/trends"
            className="group p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-amber-500/50 transition duration-300 hover:shadow-xl hover:shadow-amber-500/5"
          >
            <div className="text-amber-400 text-2xl mb-3">📈</div>
            <h2 className="text-lg font-semibold text-slate-100 group-hover:text-amber-300 transition">
              Sensor Trends
            </h2>
            <p className="text-slate-400 text-sm mt-1">
              Multi-sensor telemetry showing displacement velocity and pore pressure dynamics.
            </p>
            <span className="inline-block mt-4 text-xs font-mono text-amber-400 group-hover:translate-x-1 transition">
              View Analytics →
            </span>
          </Link>
        </div>

        {/* Footer Meta */}
        <div className="pt-8 border-t border-slate-900 flex flex-wrap items-center justify-between text-xs text-slate-500 font-mono">
          <div>Next.js 16.3.1 (App Router + Turbopack)</div>
          <div>FastAPI 0.136.x Backend Ready</div>
          <div>MapLibre GL + Recharts</div>
        </div>
      </div>
    </main>
  );
}
