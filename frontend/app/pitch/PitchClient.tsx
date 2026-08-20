'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  BarChart,
  Bar,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
  Cell,
} from 'recharts';

import {
  section01,
  section02,
  section03,
  section04,
  section05,
  section06,
  section07,
  benchmarkModels,
  glossary,
  teleprompter,
  filterPills,
  type FilterId,
  type PitchItem,
  type Flashcard,
  type GlossaryTerm,
} from './data';

import AriaTab from './AriaTab';

// ============================================================================
// Design tokens (ink-blue editorial)
// ============================================================================
const ink = '#2563EB';
const inkSoft = '#EFF4FF';
const inkDeep = '#1D4ED8';
const paper = '#FFFFFF';
const paperWarm = '#FBFBFD';
const inkDark = '#0B1220';
const hairline = '#E6E8EE';
const muted = '#5B6472';
const safe = '#047857';
const warning = '#B45309';
const danger = '#B91C1C';

import { TopBar } from '@/components/topbar/TopBar';
import { ChapterHeader } from '@/components/ui/ChapterHeader';
import { CopyButton } from '@/components/ui/CopyButton';

// ============================================================================
// Tabs — minimal underline
// ============================================================================
type TabId = 'flow' | 'defense' | 'bench' | 'tele' | 'gloss';

const tabs: { id: TabId; label: string }[] = [
  { id: 'flow', label: 'Pitch Flow' },
  { id: 'defense', label: 'Judge Traps' },
  { id: 'bench', label: 'ML Benchmark' },
  { id: 'tele', label: 'Teleprompter' },
  { id: 'gloss', label: 'Glossary' },
];

function Tabs({ active, setActive }: { active: TabId; setActive: (t: TabId) => void }) {
  return (
    <nav className="max-w-5xl mx-auto px-6 md:px-10 mt-10">
      <div className="flex flex-wrap gap-x-6 gap-y-2 border-b border-[#E6E8EE]">
        {tabs.map((t) => {
          const isActive = active === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActive(t.id)}
              className={`relative pb-3 text-[13px] font-medium tracking-tight transition ${
                isActive ? 'text-[#0B1220]' : 'text-[#5B6472] hover:text-[#0B1220]'
              }`}
            >
              {t.label}
              {isActive && (
                <span className="absolute -bottom-px left-0 right-0 h-[2px] bg-[#2563EB]" />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

// ============================================================================
// Pitch row — single Q per horizontal line
// ============================================================================
function PitchRow({ item, idx }: { item: PitchItem; idx: number }) {
  const [open, setOpen] = useState(false);
  return (
    <article className="border-b border-[#E6E8EE] py-7 first:pt-2">
      <div className="flex items-baseline gap-4 md:gap-6">
        <div className="flex-shrink-0 w-12 md:w-16 text-right">
          <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">
            Q{String(idx + 1).padStart(2, '0')}
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <button
            onClick={() => setOpen((v) => !v)}
            className="w-full text-left group flex items-start gap-4"
          >
            <h3 className="flex-1 text-[18px] md:text-[20px] font-semibold tracking-[-0.01em] text-[#0B1220] leading-[1.3] group-hover:text-[#1D4ED8] transition">
              {item.q}
            </h3>
            <span
              className={`flex-shrink-0 mt-1.5 w-5 h-5 rounded-full border border-[#E6E8EE] flex items-center justify-center text-[#5B6472] transition-transform ${
                open ? 'rotate-45 border-[#0B1220] text-[#0B1220]' : ''
              }`}
              aria-hidden
            >
              <svg viewBox="0 0 24 24" className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <path d="M12 5v14M5 12h14" />
              </svg>
            </span>
          </button>

          <div className="mt-3 rounded-md bg-[#EFF4FF] border-l-2 border-[#2563EB] px-4 py-3 text-[13.5px] text-[#0B1220] leading-relaxed">
            <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#2563EB] mr-2">
              10-sec
            </span>
            {item.short}
          </div>

          {open && (
            <div className="mt-5 space-y-5 animate-[fadeIn_180ms_ease-out]">
              <div>
                <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#8A93A1] mb-2">
                  Full defensible answer
                </div>
                <p className="text-[15px] text-[#1f2937] leading-[1.7]">{item.full}</p>
              </div>
              {item.plain && (
                <div className="rounded-md bg-emerald-50 border-l-2 border-emerald-500 px-4 py-3">
                  <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-emerald-700 mb-1">
                    In plain English
                  </div>
                  <p className="text-[14px] text-emerald-900/80 leading-[1.65]">{item.plain}</p>
                </div>
              )}
              <div className="flex items-center justify-between flex-wrap gap-3 pt-1">
                {item.tags && item.tags.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {item.tags.slice(0, 5).map((t) => (
                      <span
                        key={t}
                        className="text-[10px] font-mono uppercase tracking-[0.14em] px-2 py-0.5 rounded-full bg-white border border-[#E6E8EE] text-[#5B6472]"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span />
                )}
                <CopyButton text={`Q: ${item.q}\n\nA: ${item.full}`} />
              </div>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

// ============================================================================
// Flashcard (single full-width, click to flip)
// ============================================================================
function FlashRow({ card, idx }: { card: Flashcard; idx: number }) {
  const [flipped, setFlipped] = useState(false);
  return (
    <article className="border-b border-[#E6E8EE] py-7 first:pt-2">
      <div className="flex items-baseline gap-4 md:gap-6">
        <div className="flex-shrink-0 w-12 md:w-16 text-right">
          <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-[#B91C1C]">
            T{String(idx + 1).padStart(2, '0')}
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <button
            onClick={() => setFlipped((v) => !v)}
            className="w-full text-left group"
          >
            {!flipped ? (
              <>
                <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#B91C1C] mb-1.5">
                  The question judges will ask
                </div>
                <h3 className="text-[18px] md:text-[20px] font-semibold tracking-[-0.01em] text-[#0B1220] leading-[1.3] group-hover:text-[#B91C1C] transition">
                  {card.q}
                </h3>
                {card.doNotSay && card.doNotSay.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#B91C1C]">
                      Do not say
                    </span>
                    {card.doNotSay.map((d) => (
                      <span
                        key={d}
                        className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-50 text-[#B91C1C] border border-rose-200"
                      >
                        {d}
                      </span>
                    ))}
                  </div>
                )}
                <div className="mt-3 text-[12px] text-[#2563EB] font-medium">
                  Tap to reveal the counter-punch →
                </div>
              </>
            ) : (
              <div className="space-y-4">
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-amber-700 mb-1.5">
                    ⚠ The trap to avoid
                  </div>
                  <p className="text-[15px] text-[#1f2937] leading-[1.7]">{card.trap}</p>
                </div>
                <div className="rounded-md bg-emerald-50 border-l-2 border-emerald-600 px-4 py-3">
                  <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-emerald-700 mb-1">
                    🛡 The winning counter-punch
                  </div>
                  <p className="text-[14.5px] text-emerald-900 leading-[1.65]">{card.counter}</p>
                </div>
                <div className="flex items-center justify-between flex-wrap gap-3 pt-1">
                  <div className="text-[12px] text-[#5B6472]">
                    Original question: <span className="text-[#0B1220]">{card.q}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CopyButton
                      text={`Q: ${card.q}\n\nDO NOT SAY: ${(card.doNotSay || []).join(' | ')}\n\nCOUNTER: ${card.counter}`}
                    />
                    <span className="text-[12px] text-[#2563EB] font-medium">← flip back</span>
                  </div>
                </div>
              </div>
            )}
          </button>
        </div>
      </div>
    </article>
  );
}

// ============================================================================
// Pitch Flow tab
// ============================================================================
type Section = {
  id: string;
  title: string;
  subtitle: string;
  items: PitchItem[];
  filterId: FilterId;
};

const sections: Section[] = [
  {
    id: '01',
    title: 'Problem & Market Deep-Dive',
    subtitle:
      'The Kusmunda anchor, DGMS fatality statistics, the SSR cost barrier, and the 200+ CIL mines that need this.',
    items: section01,
    filterId: 'pitch',
  },
  {
    id: '02',
    title: 'Technical Architecture',
    subtitle:
      'Four ingest streams, FastAPI + Pydantic contracts, WebSocket 2.5s loop, MapLibre 3D pit heatmap, Open-Meteo rainfall.',
    items: section02,
    filterId: 'arch',
  },
  {
    id: '03',
    title: 'Machine Learning & Data Science',
    subtitle:
      'Class imbalance 61/26/13, Fukuzono physics, class-weighted loss vs SMOTE, temporal split, SHAP proof of learning.',
    items: section03,
    filterId: 'ml',
  },
  {
    id: '04',
    title: 'Deployment, Edge & Scaling',
    subtitle:
      'Raspberry Pi and Jetson ONNX inference, GPIO sirens, SIM800L GSM SMS, Vercel + Render split, multi-site AOI config.',
    items: section04,
    filterId: 'arch',
  },
  {
    id: '05',
    title: 'Innovation, Impact & SDGs',
    subtitle:
      'The first four-modality fusion under Fukuzono. SDG 8, 9, 11, 13 alignment. Solo 8-day sprint, ₹500 Cr disaster prevention.',
    items: section05,
    filterId: 'impact',
  },
  {
    id: '07',
    title: 'Deep Learning Benchmark (GRU vs Trees)',
    subtitle:
      'Why the GRU was benchmarked. Zero false alarms, safe failure mode, why XGBoost is still the champion.',
    items: section07,
    filterId: 'gru',
  },
];

function matchesFilter(p: PitchItem, filter: FilterId) {
  if (filter === 'all' || filter === 'pitch') return true;
  const mlTags = new Set([
    'imbalance', 'class', 'recall', 'smote', 'class-weight', 'physics', 'split', 'temporal',
    'leakage', 'features', 'input', 'vector', 'xgboost', 'randomforest', 'comparison',
    'shap', 'explainability', 'terrain', 'v2', 'label', 'fix', 'v2b', 'v2c', 'isolation',
    'gru', 'benchmark', 'honesty', 'architecture', 'training', 'precision', 'safe-failure',
  ]);
  const archTags = new Set([
    'architecture', 'pipeline', 'realtime', 'fastapi', 'backend', 'structure', 'nextjs',
    'react', 'typescript', 'map', 'maplibre', 'visualization', 'pydantic', 'contracts',
    'types', 'mock', 'real', 'migration', 'websocket', 'broadcast', 'grid', 'zone',
    'kusmunda', 'dem', 'copernicus', 'topography', 'sar', 'sentinel', 'backscatter',
    'rainfall', 'open-meteo', 'era5', 'edge', 'raspberry-pi', 'jetson', 'onnx', 'tflite',
    'sync', 'offline', 'buffer', 'scale', 'multi-site', 'config',
  ]);
  const impactTags = new Set([
    'problem', 'safety', 'bench', 'cost', 'ssr', 'market', 'dgms', 'statistics', 'manual',
    'failure', 'monsoon', 'sih', 'ministry', 'risk', 'business', 'complement', 'fusion',
    'innovation', 'fukuzono', 'sdg', 'social', 'delivery', 'sprint',
  ]);
  const gruTags = new Set([
    'gru', 'benchmark', 'honesty', 'architecture', 'training', 'precision', 'safe-failure',
    'xgboost', 'randomforest', 'comparison', 'recall',
  ]);
  if (filter === 'ml') return !!p.tags?.some((t) => mlTags.has(t));
  if (filter === 'arch') return !!p.tags?.some((t) => archTags.has(t));
  if (filter === 'impact') return !!p.tags?.some((t) => impactTags.has(t));
  if (filter === 'gru') return !!p.tags?.some((t) => gruTags.has(t));
  return true;
}

function PitchFlowTab({ query, filter }: { query: string; filter: FilterId }) {
  const visible = sections
    .filter((s) => filter === 'all' || s.filterId === filter || matchesFilter(s.items[0] || { q: '', short: '', full: '' }, filter))
    .map((s) => ({
      ...s,
      items: s.items.filter(
        (it) =>
          !query ||
          it.q.toLowerCase().includes(query.toLowerCase()) ||
          it.short.toLowerCase().includes(query.toLowerCase()) ||
          it.full.toLowerCase().includes(query.toLowerCase()) ||
          (it.plain && it.plain.toLowerCase().includes(query.toLowerCase())),
      ),
    }))
    .filter((s) => s.items.length > 0);

  if (visible.length === 0) {
    return (
      <main className="max-w-5xl mx-auto px-6 md:px-10 py-16 text-center text-[#5B6472]">
        No matching questions. Try a different keyword or clear the filter.
      </main>
    );
  }

  return (
    <main className="max-w-5xl mx-auto px-6 md:px-10 pb-24">
      {visible.map((s) => (
        <section key={s.id}>
          <ChapterHeader num={s.id} title={s.title} subtitle={s.subtitle} />
          <div>
            {s.items.map((it, i) => (
              <PitchRow key={`${s.id}-${i}`} item={it} idx={i} />
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}

// ============================================================================
// Defense tab
// ============================================================================
function DefenseTab({ query }: { query: string }) {
  const filtered = section06.filter(
    (c) =>
      !query ||
      c.q.toLowerCase().includes(query.toLowerCase()) ||
      c.trap.toLowerCase().includes(query.toLowerCase()) ||
      c.counter.toLowerCase().includes(query.toLowerCase()),
  );
  if (filtered.length === 0) {
    return (
      <main className="max-w-5xl mx-auto px-6 md:px-10 py-16 text-center text-[#5B6472]">
        No matching defenses.
      </main>
    );
  }
  return (
    <main className="max-w-5xl mx-auto px-6 md:px-10 pb-24">
      <ChapterHeader
        num="06"
        title="Judge Defense & Flashcard Arena"
        subtitle="Fifteen hard-hitting questions judges will ask. Tap any row to flip and reveal the trap to avoid plus the winning counter-punch."
      />
      <div>
        {filtered.map((c, i) => (
          <FlashRow key={i} card={c} idx={i} />
        ))}
      </div>
    </main>
  );
}

// ============================================================================
// Benchmark tab
// ============================================================================
function BenchmarkTab() {
  const chartData = benchmarkModels.map((m) => ({
    name: m.name,
    Precision: +(m.precision * 100).toFixed(2),
    Recall: +(m.recall * 100).toFixed(2),
    'F1 Score': +(m.f1 * 100).toFixed(2),
  }));

  return (
    <main className="max-w-5xl mx-auto px-6 md:px-10 pb-24">
      <ChapterHeader
        num="BENCH"
        title="ML Performance & Model Benchmark"
        subtitle="Held-out test set: 1,136 sequences · 197 Evacuation events · temporal cutoff 2026-06-03. In a life-safety system, recall on Evacuation beats precision."
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[#E6E8EE] border border-[#E6E8EE] rounded-2xl overflow-hidden">
        {benchmarkModels.map((m) => {
          const headline =
            m.tone === 'champion' ? safe : m.tone === 'strong' ? ink : warning;
          return (
            <div key={m.name} className="bg-white p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="text-[11px] font-mono uppercase tracking-[0.18em]" style={{ color: headline }}>
                  {m.tone === 'champion' ? 'Champion' : m.tone === 'strong' ? 'Fallback' : 'Benchmark'}
                </div>
                <div className="text-[13px] font-semibold text-[#0B1220]">{m.name}</div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <Metric label="Precision" value={m.precision} />
                <Metric label="Recall" value={m.recall} />
                <Metric label="F1" value={m.f1} />
              </div>
              <div className="border-t border-[#E6E8EE] pt-3 flex items-baseline justify-between">
                <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">
                  Missed evacuations
                </div>
                <div
                  className="text-[20px] font-semibold font-mono"
                  style={{ color: m.missed === 0 ? safe : m.missed <= 3 ? warning : danger }}
                >
                  {m.missed}
                  <span className="text-[#8A93A1] text-[12px]"> / {m.totalEvac}</span>
                </div>
              </div>
              <p className="text-[12.5px] text-[#5B6472] leading-relaxed">{m.note}</p>
            </div>
          );
        })}
      </div>

      <section className="mt-12">
        <h3 className="text-[20px] font-semibold tracking-[-0.01em] text-[#0B1220]">
          Precision / Recall / F1 across models
        </h3>
        <p className="text-[13px] text-[#5B6472] mt-1">
          Bars at 100% indicate a perfect score. Watch the Recall gap on GRU.
        </p>
        <div className="mt-5 h-72 w-full rounded-2xl border border-[#E6E8EE] bg-white p-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid stroke="#EEF1F5" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="name"
                stroke="#5B6472"
                fontSize={12}
                tickLine={false}
                axisLine={{ stroke: '#E6E8EE' }}
              />
              <YAxis
                stroke="#5B6472"
                fontSize={12}
                tickLine={false}
                axisLine={{ stroke: '#E6E8EE' }}
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                cursor={{ fill: 'rgba(37,99,235,0.05)' }}
                contentStyle={{
                  background: '#FFFFFF',
                  border: '1px solid #E6E8EE',
                  borderRadius: 12,
                  fontSize: 12,
                  boxShadow: '0 8px 30px rgba(15,23,42,0.08)',
                }}
                labelStyle={{ color: '#0B1220' }}
                formatter={(v) => `${Number(v).toFixed(2)}%`}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: '#5B6472' }} iconType="circle" />
              <Bar dataKey="Precision" radius={[6, 6, 0, 0]}>
                {chartData.map((_, i) => (
                  <Cell key={`p-${i}`} fill={safe} />
                ))}
              </Bar>
              <Bar dataKey="Recall" radius={[6, 6, 0, 0]}>
                {chartData.map((_, i) => (
                  <Cell key={`r-${i}`} fill={ink} />
                ))}
              </Bar>
              <Bar dataKey="F1 Score" radius={[6, 6, 0, 0]}>
                {chartData.map((_, i) => (
                  <Cell key={`f-${i}`} fill="#7C3AED" />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-6">
          <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-emerald-700">
            XGBoost · zero missed
          </div>
          <p className="mt-3 text-[14.5px] text-[#0B1220] leading-[1.7]">
            <strong style={{ color: safe }}>0 of 197</strong> evacuations were misclassified. The model is
            conservative on the Warning band: it occasionally raises a Warning that turns out to be Safe
            (false alarm), but it never lets an Evacuation event fall below Warning. That is the safety
            contract.
          </p>
        </div>
        <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-6">
          <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-amber-700">
            GRU · safe failure mode
          </div>
          <p className="mt-3 text-[14.5px] text-[#0B1220] leading-[1.7]">
            All <strong style={{ color: warning }}>55 misses</strong> landed in the Warning class, not Safe.
            Zero false alarms (1.0000 precision) and zero Evacuation-to-Safe catastrophic misses. The GRU
            degrades into a cautious Warning generator — the safest way an AI can be wrong.
          </p>
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">{label}</div>
      <div className="mt-1 text-[22px] font-semibold tracking-[-0.01em] text-[#0B1220] font-mono">
        {(value * 100).toFixed(2)}
        <span className="text-[#8A93A1] text-[12px]">%</span>
      </div>
    </div>
  );
}

// ============================================================================
// Teleprompter tab
// ============================================================================
function TeleprompterTab() {
  const [big, setBig] = useState(false);
  return (
    <main className="max-w-3xl mx-auto px-6 md:px-10 pb-24">
      <ChapterHeader
        num="TELE"
        title="Presenter Teleprompter"
        subtitle="Large-text, distraction-free view for a teammate holding a phone or tablet while presenting."
      />
      <div className="flex justify-end -mt-4 mb-4">
        <button
          onClick={() => setBig((v) => !v)}
          className="px-3.5 py-1.5 text-[12px] font-medium rounded-full bg-white border border-[#E6E8EE] text-[#0B1220] hover:border-[#0B1220] transition"
        >
          {big ? 'Normal text' : 'Bigger text'}
        </button>
      </div>
      {teleprompter.map((seg) => (
        <article key={seg.minute} className="border-b border-[#E6E8EE] py-8 first:pt-2">
          <div className="flex items-baseline gap-3">
            <span className="text-[11px] font-mono uppercase tracking-[0.22em] text-[#2563EB]">
              {seg.minute}
            </span>
            <h3
              className={`font-semibold tracking-[-0.01em] text-[#0B1220] ${
                big ? 'text-[28px] md:text-[34px]' : 'text-[22px] md:text-[26px]'
              }`}
            >
              {seg.title}
            </h3>
          </div>
          <ul
            className={`mt-5 space-y-3 text-[#0B1220] leading-[1.75] ${
              big ? 'text-[18px] md:text-[20px]' : 'text-[15px] md:text-[16px]'
            }`}
          >
            {seg.points.map((p, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="mt-[10px] w-1.5 h-1.5 rounded-full bg-[#2563EB] flex-shrink-0" />
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </article>
      ))}
      <div className="mt-10 rounded-2xl border border-[#E6E8EE] bg-white p-5 text-[13px] text-[#5B6472] leading-relaxed">
        <strong className="text-[#0B1220]">Pro tip —</strong> pair this view with the Rehearsal Timer
        (top right). 3-min, 5-min, and 7-min countdown modes are preconfigured for short, standard, and
        deep-dive pitches.
      </div>
    </main>
  );
}

// ============================================================================
// Glossary tab
// ============================================================================
function GlossaryRow({ term, defaultOpen }: { term: GlossaryTerm; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(!!defaultOpen);
  return (
    <article className="border-b border-[#E6E8EE] py-6 first:pt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left flex items-baseline gap-4 md:gap-6"
      >
        <div className="flex-shrink-0 w-12 md:w-16 text-right">
          <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">Term</div>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-[18px] md:text-[20px] font-semibold tracking-[-0.01em] text-[#2563EB]">
            {term.term}
          </h3>
          <p className="mt-1.5 text-[15px] text-[#0B1220] leading-[1.65]">{term.plain}</p>
        </div>
        <span
          className={`flex-shrink-0 mt-1 w-5 h-5 rounded-full border border-[#E6E8EE] flex items-center justify-center text-[#5B6472] transition-transform ${
            open ? 'rotate-45 border-[#0B1220] text-[#0B1220]' : ''
          }`}
          aria-hidden
        >
          <svg viewBox="0 0 24 24" className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </span>
      </button>
      {open && term.detail && (
        <div className="mt-4 ml-12 md:ml-[88px] text-[14px] text-[#5B6472] leading-[1.7] border-l-2 border-[#E6E8EE] pl-4">
          {term.detail}
        </div>
      )}
    </article>
  );
}

function GlossaryTab({ query }: { query: string }) {
  const filtered = glossary.filter(
    (t) =>
      !query ||
      t.term.toLowerCase().includes(query.toLowerCase()) ||
      t.plain.toLowerCase().includes(query.toLowerCase()) ||
      (t.detail && t.detail.toLowerCase().includes(query.toLowerCase())),
  );
  if (filtered.length === 0) {
    return (
      <main className="max-w-5xl mx-auto px-6 md:px-10 py-16 text-center text-[#5B6472]">
        No matching terms.
      </main>
    );
  }
  return (
    <main className="max-w-5xl mx-auto px-6 md:px-10 pb-24">
      <ChapterHeader
        num="LEX"
        title="Non-Tech Glossary"
        subtitle="Plain-English translations for non-tech teammates. Click any term for the deeper explanation."
      />
      <div>
        {filtered.map((t, i) => (
          <GlossaryRow key={t.term} term={t} defaultOpen={i < 3} />
        ))}
      </div>
    </main>
  );
}

// ============================================================================
// Timer modal — light theme
// ============================================================================
function TimerModal({ onClose }: { onClose: () => void }) {
  const [totalSec, setTotalSec] = useState(180);
  const [remaining, setRemaining] = useState(180);
  const [running, setRunning] = useState(false);
  const audioCtxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          setRunning(false);
          beep();
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [running]);

  function beep() {
    try {
      if (!audioCtxRef.current) {
        const AC =
          (window as unknown as { AudioContext?: typeof AudioContext; webkitAudioContext?: typeof AudioContext }).AudioContext ||
          (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
        if (!AC) return;
        audioCtxRef.current = new AC();
      }
      const ctx = audioCtxRef.current;
      const now = ctx.currentTime;
      [0, 0.25, 0.5].forEach((offset) => {
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.type = 'sine';
        o.frequency.value = 880;
        g.gain.setValueAtTime(0.0001, now + offset);
        g.gain.exponentialRampToValueAtTime(0.25, now + offset + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, now + offset + 0.18);
        o.connect(g).connect(ctx.destination);
        o.start(now + offset);
        o.stop(now + offset + 0.2);
      });
    } catch {
      /* no-op */
    }
  }

  function pick(min: number) {
    setTotalSec(min * 60);
    setRemaining(min * 60);
    setRunning(false);
  }

  const pct = totalSec === 0 ? 0 : (remaining / totalSec) * 100;
  const mm = Math.floor(remaining / 60).toString().padStart(2, '0');
  const ss = (remaining % 60).toString().padStart(2, '0');
  const urgent = remaining <= 30 && remaining > 0;
  const finished = remaining === 0;

  let barColor = safe;
  if (urgent) barColor = warning;
  if (finished) barColor = danger;

  return (
    <div
      className="fixed inset-0 z-50 bg-[#0B1220]/40 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-3xl bg-white border border-[#E6E8EE] p-7 shadow-2xl shadow-slate-900/20"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#2563EB]">
              Rehearsal Timer
            </div>
            <h3 className="mt-1 text-[18px] font-semibold text-[#0B1220]">Pick a duration</h3>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full text-[#5B6472] hover:text-[#0B1220] hover:bg-[#F2F4F8] transition flex items-center justify-center"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="flex gap-2 mb-7">
          {[3, 5, 7].map((m) => {
            const active = totalSec === m * 60;
            return (
              <button
                key={m}
                onClick={() => pick(m)}
                className={`flex-1 py-2 text-[13px] font-mono rounded-full border transition ${
                  active
                    ? 'bg-[#0B1220] text-white border-[#0B1220]'
                    : 'bg-white text-[#0B1220] border-[#E6E8EE] hover:border-[#0B1220]'
                }`}
              >
                {m} min
              </button>
            );
          })}
        </div>

        <div
          className="text-center font-mono text-[68px] md:text-[84px] font-semibold tracking-[-0.04em]"
          style={{ color: finished ? danger : urgent ? warning : inkDark }}
        >
          {mm}:{ss}
        </div>

        <div className="mt-5 h-1.5 rounded-full bg-[#F2F4F8] overflow-hidden">
          <div
            className="h-full transition-all duration-500"
            style={{ width: `${pct}%`, backgroundColor: barColor }}
          />
        </div>

        <div className="flex gap-2 mt-6">
          <button
            onClick={() => setRunning((v) => !v)}
            disabled={finished}
            className="flex-1 py-2.5 text-[13px] font-semibold rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:bg-[#E6E8EE] disabled:text-[#8A93A1] text-white transition shadow-sm"
          >
            {finished ? 'Time up' : running ? 'Pause' : 'Start'}
          </button>
          <button
            onClick={() => {
              setRunning(false);
              setRemaining(totalSec);
            }}
            className="px-5 py-2.5 text-[13px] font-medium rounded-full bg-white border border-[#E6E8EE] text-[#0B1220] hover:border-[#0B1220] transition"
          >
            Reset
          </button>
        </div>

        {finished && (
          <div className="mt-5 text-center text-[12px] text-[#5B6472]">
            Beeped at 0s. Aim to land the close before the second beep.
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Chat drawer — opens on chat-icon click, hidden by default
// ============================================================================
function ChatDrawer({ onClose }: { onClose: () => void }) {
  // Lock body scroll while drawer is open
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-label="AI Helper chat"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-[#0B1220]/40 backdrop-blur-[3px] animate-[fadeIn_180ms_ease-out]"
        onClick={onClose}
      />

      {/* Drawer panel */}
      <div className="relative w-full sm:max-w-xl md:max-w-2xl h-full bg-white border-l border-[#E6E8EE] shadow-2xl shadow-slate-950/20 flex flex-col animate-[slideInRight_220ms_cubic-bezier(0.16,1,0.3,1)] overflow-hidden">
        <AriaTab onClose={onClose} />
      </div>

      <style jsx global>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); }
          to   { transform: translateX(0); }
        }
      `}</style>
    </div>
  );
}

// ============================================================================
// Page shell
// ============================================================================
export default function PitchClient() {
  const [tab, setTab] = useState<TabId>('flow');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<FilterId>('all');
  const [timerOpen, setTimerOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    if (query) setTab('flow');
  }, [query]);

  useEffect(() => {
    if (!chatOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setChatOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [chatOpen]);

  const totalMatches = useMemo(() => {
    if (!query) return 0;
    const q = query.toLowerCase();
    const c = (s: string) => s.toLowerCase().includes(q);
    return (
      [...section01, ...section02, ...section03, ...section04, ...section05, ...section07].filter(
        (it) => c(it.q) || c(it.short) || c(it.full) || (it.plain && c(it.plain)),
      ).length +
      section06.filter((it) => c(it.q) || c(it.trap) || c(it.counter)).length +
      glossary.filter((t) => c(t.term) || c(t.plain) || (t.detail && c(t.detail))).length
    );
  }, [query]);

  return (
    <div className="min-h-screen text-[#0B1220]" style={gradientStyle}>
      <TopBar
        query={query}
        setQuery={setQuery}
        activeFilter={filter}
        setActiveFilter={setFilter}
        filterPills={filterPills}
        onOpenTimer={() => setTimerOpen(true)}
        onOpenChat={() => setChatOpen(true)}
      />

      <Tabs active={tab} setActive={setTab} />

      {query && (
        <div className="max-w-5xl mx-auto px-6 md:px-10 mt-6">
          <div className="rounded-full bg-white border border-[#E6E8EE] px-4 py-2 text-[12.5px] text-[#5B6472] inline-flex items-center gap-2 shadow-sm">
            <svg
              className="w-3.5 h-3.5 text-[#2563EB]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            <span>
              <strong className="text-[#0B1220]">{totalMatches}</strong> matches across the hub
              for &ldquo;{query}&rdquo;
            </span>
          </div>
        </div>
      )}

      {tab === 'flow' && <PitchFlowTab query={query} filter={filter} />}
      {tab === 'defense' && <DefenseTab query={query} />}
      {tab === 'bench' && <BenchmarkTab />}
      {tab === 'tele' && <TeleprompterTab />}
      {tab === 'gloss' && <GlossaryTab query={query} />}

      {timerOpen && <TimerModal onClose={() => setTimerOpen(false)} />}

      {chatOpen && <ChatDrawer onClose={() => setChatOpen(false)} />}

      <style jsx global>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(2px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

const gradientStyle: React.CSSProperties = {
  background:
    'radial-gradient(1200px 600px at 50% -200px, #EFF4FF 0%, #F7F9FF 35%, #FFFFFF 70%)',
  backgroundAttachment: 'fixed',
};
