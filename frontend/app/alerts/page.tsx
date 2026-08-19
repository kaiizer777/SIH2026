import React from 'react';
import Link from 'next/link';
import { Alert } from '@/types';

const mockAlerts: Alert[] = [
  {
    id: 'ALT-9042',
    timestamp: '2026-08-19T14:15:00Z',
    level: 'Evacuation',
    zone: 'North Highwall - Bench 4',
    sensorId: 'RADAR-01',
    message: 'Inverse-velocity threshold breached: 1.8mm/day acceleration detected. Immediate evacuation recommended.',
    probability: 0.88,
    status: 'active',
  },
  {
    id: 'ALT-9041',
    timestamp: '2026-08-19T13:45:00Z',
    level: 'Warning',
    zone: 'East Haul Road - Ramp 2',
    sensorId: 'EXT-08',
    message: 'Extensometer pore pressure surge (+32 kPa) following rainfall event.',
    probability: 0.58,
    status: 'acknowledged',
  },
  {
    id: 'ALT-9039',
    timestamp: '2026-08-19T10:12:00Z',
    level: 'Safe',
    zone: 'South Slope Bench',
    sensorId: 'SEIS-03',
    message: 'Micro-seismic tremors normalized below background baseline.',
    probability: 0.12,
    status: 'resolved',
  },
];

export default function AlertsPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-rose-400 text-xs font-mono tracking-wide uppercase">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
            Active Warning System
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight mt-1 text-slate-50">
            Real-Time Alert Dispatch & Incident Logs
          </h1>
          <p className="text-slate-400 text-sm mt-0.5">
            Automated threshold triggers and AI rockfall risk notifications
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
            href="/trends"
            className="px-4 py-2 text-sm font-medium rounded-lg bg-sky-600 hover:bg-sky-500 text-white transition shadow-lg shadow-sky-900/30"
          >
            Telemetry Trends
          </Link>
        </div>
      </div>

      {/* Alert Cards */}
      <div className="space-y-4">
        {mockAlerts.map((alert) => {
          const badgeColor =
            alert.level === 'Evacuation'
              ? 'bg-red-500/20 text-red-400 border-red-500/40'
              : alert.level === 'Warning'
              ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
              : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';

          return (
            <div
              key={alert.id}
              className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4 transition hover:border-slate-700"
            >
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeColor}`}>
                    {alert.level.toUpperCase()}
                  </span>
                  <span className="font-mono text-xs text-slate-400">{alert.id}</span>
                  <span className="text-xs text-slate-400">• {new Date(alert.timestamp).toLocaleTimeString()}</span>
                </div>
                <div className="font-semibold text-slate-100 text-base">{alert.zone}</div>
                <p className="text-slate-300 text-sm max-w-3xl leading-relaxed">{alert.message}</p>
                <div className="flex items-center gap-4 text-xs font-mono text-slate-400 pt-1">
                  <span>Sensor: {alert.sensorId || 'Radar Array'}</span>
                  <span>Rockfall Probability: {(alert.probability * 100).toFixed(0)}%</span>
                  <span>Status: <strong className="uppercase text-slate-200">{alert.status}</strong></span>
                </div>
              </div>

              <div className="flex items-center gap-2 self-start md:self-center">
                {alert.status === 'active' && (
                  <button className="px-3 py-1.5 text-xs font-medium rounded-lg bg-rose-600 hover:bg-rose-500 text-white transition">
                    Acknowledge & Siren
                  </button>
                )}
                <button className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition">
                  Dispatch Geotech Team
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
