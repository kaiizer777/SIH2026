import React from 'react';
import Link from 'next/link';
import { TopBar } from '@/components/topbar/TopBar';
import { ChapterHeader } from '@/components/ui/ChapterHeader';

const routes = [
  {
    num: '01',
    href: '/dashboard',
    title: 'Open-Pit Spatial Risk Dashboard',
    desc: 'Interactive 3D WebGL heatmap of mine benches with real-time zone-level risk scoring and sensor placement.',
    badge: 'Live Map',
  },
  {
    num: '02',
    href: '/alerts',
    title: 'Real-Time Alert Dispatch & Incident Logs',
    desc: 'Automated evacuation threshold triggers, audible siren dispatch status, and geotech team response audit trail.',
    badge: 'Dispatch',
  },
  {
    num: '03',
    href: '/trends',
    title: 'Geotechnical Telemetry & Trend Analytics',
    desc: 'Multi-sensor time-series showing displacement velocity, Fukuzono acceleration, and pore-pressure dynamics.',
    badge: 'Telemetry',
  },
  {
    num: '04',
    href: '/pitch',
    title: 'Pitch Companion & Defense Rehearsal Hub',
    desc: 'Master repository of 90+ technical defenses, ML benchmark metrics (XGBoost vs GRU), teleprompter, and glossary.',
    badge: 'Master Hub',
  },
];

const systemSpecs = [
  {
    eyebrow: 'Ingest & Telemetry',
    headline: '24 Sensor Streams',
    detail: 'Sub-millimeter radar displacement, extensometer pore pressure, and Open-Meteo rainfall feeds on a 2.5s loop.',
  },
  {
    eyebrow: 'ML Architecture',
    headline: '100% Recall Champion',
    detail: 'Class-weighted XGBoost under Fukuzono inverse-velocity physics. 0 missed evacuations across 197 test events.',
  },
  {
    eyebrow: 'Production Deployment',
    headline: 'Edge & Cloud Split',
    detail: 'Next.js 16 App Router + FastAPI Pydantic contracts with ONNX edge inference and GSM siren fallback.',
  },
];

export default function Home() {
  return (
    <div className="min-h-screen text-[#0B1220]" style={gradientStyle}>
      <TopBar showSearch={false} activeRoute="/" />

      <main className="max-w-5xl mx-auto px-5 sm:px-6 md:px-10 pb-24 pt-8 md:pt-12">
        {/* Editorial Eyebrow & Intro */}
        <div className="space-y-4">
          <div className="flex items-baseline gap-3">
            <span className="text-[11px] font-mono uppercase tracking-[0.22em] text-[#2563EB]">
              SIH25071 • GEOTECHNICAL SURVEILLANCE
            </span>
            <span className="flex-1 h-px bg-[#E6E8EE]" />
          </div>

          <h1 className="text-[32px] sm:text-[40px] md:text-[48px] font-semibold tracking-[-0.03em] text-[#0B1220] leading-[1.1] max-w-3xl">
            AI-Based Rockfall Prediction &amp; Early Warning System
          </h1>

          <p className="text-[16px] md:text-[17px] text-[#5B6472] max-w-2xl leading-[1.7]">
            Continuous open-pit slope stability surveillance combining inverse-velocity displacement
            modeling, multi-sensor telemetry, and spatial risk heatmaps for smart mine safety.
          </p>
        </div>

        {/* Route Navigation Rows */}
        <section className="mt-12 md:mt-16">
          <div className="flex items-baseline justify-between border-b border-[#E6E8EE] pb-3">
            <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">
              System Routes
            </span>
            <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">
              Select Destination →
            </span>
          </div>

          <div className="divide-y divide-[#E6E8EE]">
            {routes.map((r) => (
              <Link
                key={r.href}
                href={r.href}
                className="group block py-7 first:pt-6 transition hover:bg-[#EFF4FF]/40 -mx-4 px-4 rounded-xl"
              >
                <div className="flex items-baseline gap-4 md:gap-6">
                  <div className="flex-shrink-0 w-10 md:w-12 text-right">
                    <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#8A93A1] group-hover:text-[#2563EB] transition">
                      {r.num}
                    </span>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <h2 className="text-[18px] md:text-[21px] font-semibold tracking-[-0.01em] text-[#0B1220] group-hover:text-[#2563EB] transition flex items-center gap-2">
                          <span>→</span>
                          <span>{r.title}</span>
                        </h2>
                      </div>
                      <span className="hidden sm:inline-flex text-[10px] font-mono uppercase tracking-[0.18em] px-2.5 py-1 rounded-full bg-white border border-[#E6E8EE] text-[#5B6472] group-hover:border-[#2563EB] group-hover:text-[#2563EB] transition">
                        {r.badge}
                      </span>
                    </div>

                    <p className="mt-1.5 text-[14px] md:text-[15px] text-[#5B6472] leading-[1.65]">
                      {r.desc}
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* System Architecture Specs Hairline Block */}
        <section className="mt-16 md:mt-20">
          <ChapterHeader
            num="SPEC"
            title="System Specifications"
            subtitle="Built for zero false-negative tolerance in open-cast coal and metal mining operations."
          />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[#E6E8EE] border border-[#E6E8EE] rounded-2xl overflow-hidden mt-6">
            {systemSpecs.map((spec) => (
              <div key={spec.eyebrow} className="bg-white p-6 space-y-3">
                <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#2563EB]">
                  {spec.eyebrow}
                </div>
                <div className="text-[17px] font-semibold text-[#0B1220] tracking-tight">
                  {spec.headline}
                </div>
                <p className="text-[13px] text-[#5B6472] leading-relaxed">{spec.detail}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Footer Meta */}
        <footer className="mt-16 pt-8 border-t border-[#E6E8EE] flex flex-wrap items-center justify-between gap-3 text-[11px] text-[#8A93A1] font-mono uppercase tracking-[0.14em]">
          <div>Next.js 16 App Router • React 19</div>
          <div>FastAPI 0.136.x Real-Time Feed</div>
          <div>MapLibre GL • WebGL 2.0</div>
        </footer>
      </main>
    </div>
  );
}

const gradientStyle: React.CSSProperties = {
  background:
    'radial-gradient(1200px 600px at 50% -200px, #EFF4FF 0%, #F7F9FF 35%, #FFFFFF 70%)',
  backgroundAttachment: 'fixed',
};
