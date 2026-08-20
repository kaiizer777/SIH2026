'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { TopBar } from '@/components/topbar/TopBar';
import { ChapterHeader } from '@/components/ui/ChapterHeader';

// Dynamically import PitHeatmap since MapLibre uses browser window/canvas
const PitHeatmap = dynamic(() => import('@/components/map/PitHeatmap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[520px] flex items-center justify-center bg-[#FBFBFD] rounded-2xl border border-[#E6E8EE] animate-pulse text-[#5B6472] font-mono text-sm">
      Loading Open-Pit 3D Heatmap...
    </div>
  ),
});

const metrics = [
  {
    label: 'Active Sensors',
    value: '24 / 24',
    status: '100% Operational',
    tone: 'safe',
  },
  {
    label: 'Critical Sectors',
    value: '1 Zone',
    status: 'North Highwall (Evac)',
    tone: 'danger',
  },
  {
    label: 'Max Velocity',
    value: '1.80 mm/d',
    status: 'Inverse-Vel Trigger',
    tone: 'warning',
  },
  {
    label: 'Model Confidence',
    value: '94.8%',
    status: 'Ensemble (GRU + XGB)',
    tone: 'ink',
  },
];

const sectorRisks = [
  { id: 'Z01', name: 'North Highwall - Bench 4', risk: 'Evacuation', score: '0.88', status: 'Active Siren' },
  { id: 'Z02', name: 'East Haul Road - Ramp 2', risk: 'Warning', score: '0.58', status: 'Under Watch' },
  { id: 'Z03', name: 'South Slope Bench', risk: 'Safe', score: '0.12', status: 'Nominal' },
  { id: 'Z04', name: 'West Pit Crest', risk: 'Safe', score: '0.08', status: 'Nominal' },
];

export default function DashboardPage() {
  return (
    <div className="min-h-screen text-[#0B1220]" style={gradientStyle}>
      <TopBar showSearch={false} activeRoute="/dashboard" />

      <main className="max-w-5xl mx-auto px-5 sm:px-6 md:px-10 pb-24 pt-6 md:pt-10 space-y-10">
        <ChapterHeader
          num="LIVE"
          title="Open-Pit Spatial Risk Dashboard"
          subtitle="Real-time 3D telemetry visualization, inverse-velocity displacement modeling, and zone-level rockfall risk scoring."
        />

        {/* 4-Stat Hairline Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-[#E6E8EE] border border-[#E6E8EE] rounded-2xl overflow-hidden shadow-sm">
          {metrics.map((m) => {
            const toneColor =
              m.tone === 'safe'
                ? '#047857'
                : m.tone === 'danger'
                ? '#B91C1C'
                : m.tone === 'warning'
                ? '#B45309'
                : '#2563EB';

            return (
              <div key={m.label} className="bg-white p-5 space-y-2">
                <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">
                  {m.label}
                </div>
                <div className="text-[26px] font-semibold tracking-[-0.02em] text-[#0B1220] font-mono">
                  {m.value}
                </div>
                <div className="text-[12px] font-medium" style={{ color: toneColor }}>
                  {m.status}
                </div>
              </div>
            );
          })}
        </div>

        {/* Main Map Container */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-[18px] md:text-[20px] font-semibold tracking-[-0.01em] text-[#0B1220]">
              Pit Spatial Heatmap
            </h2>
            <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">
              MapLibre WebGL • Live GPS
            </span>
          </div>

          <PitHeatmap />
        </section>

        {/* Hairline Sector Status Table / Rows */}
        <section className="space-y-4 pt-4">
          <div className="flex items-baseline justify-between border-b border-[#E6E8EE] pb-3">
            <h2 className="text-[18px] md:text-[20px] font-semibold tracking-[-0.01em] text-[#0B1220]">
              Key Sector Status Audit
            </h2>
            <Link
              href="/alerts"
              className="text-[12px] text-[#2563EB] font-medium hover:underline"
            >
              View Full Alert Dispatch Log →
            </Link>
          </div>

          <div className="divide-y divide-[#E6E8EE]">
            {sectorRisks.map((sec) => (
              <div key={sec.id} className="py-4 flex items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <span className="text-[11px] font-mono text-[#8A93A1] w-10 text-right">
                    {sec.id}
                  </span>
                  <div>
                    <div className="text-[14.5px] font-medium text-[#0B1220]">{sec.name}</div>
                    <div className="text-[12px] text-[#5B6472] font-mono">
                      Risk Score: <strong className="text-[#0B1220]">{sec.score}</strong>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`text-[10px] font-mono uppercase tracking-[0.14em] px-2.5 py-0.5 rounded-full border ${
                      sec.risk === 'Evacuation'
                        ? 'bg-rose-50 text-[#B91C1C] border-rose-200'
                        : sec.risk === 'Warning'
                        ? 'bg-amber-50 text-[#B45309] border-amber-200'
                        : 'bg-emerald-50 text-[#047857] border-emerald-200'
                    }`}
                  >
                    {sec.risk}
                  </span>
                  <span className="hidden sm:inline-block text-[12px] text-[#5B6472] font-medium">
                    {sec.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

const gradientStyle: React.CSSProperties = {
  background:
    'radial-gradient(1200px 600px at 50% -200px, #EFF4FF 0%, #F7F9FF 35%, #FFFFFF 70%)',
  backgroundAttachment: 'fixed',
};
