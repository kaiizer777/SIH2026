import React from 'react';
import { TopBar } from '@/components/topbar/TopBar';
import { ChapterHeader } from '@/components/ui/ChapterHeader';
import { TrendChart } from '@/components/charts';

export default function TrendsPage() {
  return (
    <div className="min-h-screen text-[#0B1220]" style={gradientStyle}>
      <TopBar showSearch={false} activeRoute="/trends" />

      <main className="max-w-5xl mx-auto px-5 sm:px-6 md:px-10 pb-24 pt-6 md:pt-10 space-y-10">
        <ChapterHeader
          num="TELE"
          title="Geotechnical Telemetry & Trend Analytics"
          subtitle="Real-time multi-parameter sensor feeds (Displacement, Velocity, Pore Pressure) across open-pit mine sectors."
        />

        {/* 10-Second Physical Law Callout */}
        <div className="rounded-md bg-[#EFF4FF] border-l-2 border-[#2563EB] px-4 py-3.5 text-[14px] text-[#0B1220] leading-relaxed">
          <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#2563EB] mr-2">
            Fukuzono Law
          </span>
          As slope creep accelerates toward tertiary failure, the inverse velocity <code className="font-mono text-[13px] bg-white px-1.5 py-0.5 rounded border border-[#E6E8EE] text-[#0B1220]">1 / v</code> linearly approaches zero. Real-time radar displacement curves below pinpoint the exact inflection.
        </div>

        {/* Charts Stack */}
        <section className="space-y-8">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#B91C1C] mb-2">
              Critical Sector 01 • North Highwall
            </div>
            <TrendChart
              title="North Highwall Sector (Bench 4 - Evacuation Zone)"
              subtitle="Tertiary acceleration phase detected. Displacement velocity exceeded 1.80 mm/day threshold."
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
          </div>

          <div>
            <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#B45309] mb-2">
              Monitored Corridor • East Haul Road
            </div>
            <TrendChart
              title="East Haul Road (Ramp 2 Safety Corridor)"
              subtitle="Steady-state secondary creep with moderate pore pressure increase post-rainfall."
              zoneId="zone_02"
              data={[
                { time: '08:00', displacement: 0.5, velocity: 0.02, porePressure: 22 },
                { time: '10:00', displacement: 0.6, velocity: 0.03, porePressure: 24 },
                { time: '12:00', displacement: 0.8, velocity: 0.05, porePressure: 28 },
                { time: '14:00', displacement: 1.1, velocity: 0.09, porePressure: 35 },
                { time: '16:00', displacement: 1.3, velocity: 0.1, porePressure: 37 },
                { time: '18:00', displacement: 1.5, velocity: 0.12, porePressure: 40 },
              ]}
            />
          </div>

          <div>
            <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#047857] mb-2">
              Baseline Control • South Slope
            </div>
            <TrendChart
              title="South Slope Crest (Baseline Reference)"
              subtitle="Nominal background baseline. No accelerated displacement or pore pressure elevation."
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
