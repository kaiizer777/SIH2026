'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';

// ============================================================================
// AriaTab — RAG AI Pitch Assistant for SIH 2026 Pitch Companion
// Clean editorial ink-blue styling with topic filtering and zero overflow.
// ============================================================================

type ChatMessage = { role: 'user' | 'assistant'; content: string };

export type RetrievedSource = {
  tab: string;
  section: string;
  title: string;
  body: string;
  meta?: string;
  score: number;
};

type RagApiResponse = {
  answer: string;
  sources: RetrievedSource[];
  intent: string;
  model: string;
  usage?: { total_tokens?: number };
};

type RagApiError = { error: string; detail?: string };

// Topic Filter categories
export type TopicCategory =
  | 'all'
  | 'ml'
  | 'arch'
  | 'traps'
  | 'econ'
  | 'geotech'
  | 'script';

export const TOPIC_FILTERS: { id: TopicCategory; label: string; icon: string }[] = [
  { id: 'all', label: 'All Topics', icon: '✨' },
  { id: 'ml', label: 'ML & Metrics', icon: '📊' },
  { id: 'arch', label: 'Architecture', icon: '🏗️' },
  { id: 'traps', label: 'Judge Traps', icon: '🛡️' },
  { id: 'econ', label: 'Economics & SSR', icon: '💰' },
  { id: 'geotech', label: 'Geotech & Physics', icon: '📉' },
  { id: 'script', label: 'Pitch Script', icon: '🎙️' },
];

export type PriorityPrompt = {
  category: TopicCategory;
  categoryLabel: string;
  badge: string;
  icon: string;
  label: string;
  prompt: string;
};

// Curated Top-Priority Questions per Domain for SIH 2026
const TOP_PRIORITY_PROMPTS: PriorityPrompt[] = [
  // ML & Benchmarks
  {
    category: 'ml',
    categoryLabel: 'ML & Metrics',
    badge: '100% Recall',
    icon: '📊',
    label: 'Model Accuracy & Recall Numbers',
    prompt:
      'How accurate is our ML model? Give me the exact benchmark numbers (Recall, Precision, F1) and explain what 100% recall on evacuation means in plain English.',
  },
  {
    category: 'ml',
    categoryLabel: 'ML & Metrics',
    badge: 'Class Imbalance',
    icon: '⚖️',
    label: 'Why Class-Weighted Loss vs SMOTE?',
    prompt:
      'A judge asks "why class-weighted loss instead of SMOTE for extreme class imbalance?" Give the trap to avoid and our technical defense.',
  },
  {
    category: 'ml',
    categoryLabel: 'ML & Metrics',
    badge: 'Temporal Modeling',
    icon: '🧠',
    label: 'Why GRU alongside Random Forest?',
    prompt:
      'Why did we use a GRU neural network alongside Random Forest for temporal sequence modeling of sensor data?',
  },
  {
    category: 'ml',
    categoryLabel: 'ML & Metrics',
    badge: 'Explainability',
    icon: '🔍',
    label: 'SHAP Explainability & Top Features',
    prompt:
      'How does SHAP explainability work in our rockfall detection model, and which sensor features have the highest importance?',
  },
  {
    category: 'ml',
    categoryLabel: 'ML & Metrics',
    badge: 'Alarm Fatigue',
    icon: '🚨',
    label: 'False Alarm Rate (94.2% Precision)',
    prompt:
      'What is our false alarm rate and how do we prevent alarm fatigue among opencast mine operators?',
  },

  // Architecture & Pipeline
  {
    category: 'arch',
    categoryLabel: 'Architecture',
    badge: 'System Flow',
    icon: '🏗️',
    label: 'End-to-End Pipeline in 45 Seconds',
    prompt:
      'Explain the full end-to-end architecture from IoT sensors and Sentinel-1 satellite radar to edge alerts in 45 seconds.',
  },
  {
    category: 'arch',
    categoryLabel: 'Architecture',
    badge: 'Edge / Offline',
    icon: '📡',
    label: 'Offline-First Haul Truck Alerts',
    prompt:
      'How does our system alert haul-truck drivers if the mine pit loses internet or 4G connectivity?',
  },
  {
    category: 'arch',
    categoryLabel: 'Architecture',
    badge: 'Real-Time Feed',
    icon: '⚡',
    label: 'Physics-Informed WebSocket Engine',
    prompt:
      'How does the real-time WebSocket feed integrate sensor streams with the physics-informed terrain multiplier?',
  },
  {
    category: 'arch',
    categoryLabel: 'Architecture',
    badge: 'Satellite InSAR',
    icon: '🛰️',
    label: 'GEE Sentinel-1 SAR Sync Pipeline',
    prompt:
      'How do we fetch and process Google Earth Engine Sentinel-1 SAR imagery without hitting quota limits or latency bottlenecks?',
  },
  {
    category: 'arch',
    categoryLabel: 'Architecture',
    badge: 'Data Security',
    icon: '🔒',
    label: 'Data Privacy & Mine Data Retention',
    prompt:
      'How do we guarantee data privacy for mine operators like SECL with our 7-year audit retention and zero cloud lock-in?',
  },

  // Judge Traps & Defenses
  {
    category: 'traps',
    categoryLabel: 'Judge Traps',
    badge: 'Must-Defend',
    icon: '🛡️',
    label: 'Defend: "Your Data is Synthetic"',
    prompt:
      'A judge says "your data is synthetic so this is not real." What is the trap to avoid and the winning counter-punch?',
  },
  {
    category: 'traps',
    categoryLabel: 'Judge Traps',
    badge: 'InSAR Cadence',
    icon: '🎯',
    label: 'Defend: "InSAR Takes 6-12 Days"',
    prompt:
      'A judge asks "Sentinel-1 InSAR revisits take 6-12 days, how can you catch rapid rockfalls?" What is the winning counter-punch?',
  },
  {
    category: 'traps',
    categoryLabel: 'Judge Traps',
    badge: 'Metric Trap',
    icon: '🥊',
    label: 'Defend: "What if Model Always Says Safe?"',
    prompt:
      'A judge asks "with 99% non-events, what if your model just always outputs safe?" How do we mathematically disprove this?',
  },
  {
    category: 'traps',
    categoryLabel: 'Judge Traps',
    badge: 'Simplicity Trap',
    icon: '🧱',
    label: 'Defend: "Why Not Simple Thresholds?"',
    prompt:
      'A judge asks "why use ML when you could just trigger alarms at a simple displacement threshold?" What is our defense?',
  },
  {
    category: 'traps',
    categoryLabel: 'Judge Traps',
    badge: 'Economic Trap',
    icon: '💰',
    label: 'Defend: "Cost of False Evacuation"',
    prompt:
      'A judge asks "what is the cost of a false alarm evacuation in an open-pit mine?" How do we justify our precision?',
  },

  // Economics & SSR
  {
    category: 'econ',
    categoryLabel: 'Economics & SSR',
    badge: 'Cost Barrier',
    icon: '💸',
    label: 'Cost of SSR Radar vs Our Solution',
    prompt:
      'What is the cost of industry-standard SSR slope stability radar, and why does that leave 90% of Indian mines unprotected?',
  },
  {
    category: 'econ',
    categoryLabel: 'Economics & SSR',
    badge: 'Market Target',
    icon: '🏢',
    label: '200+ CIL Opencast Mines Market',
    prompt:
      'What is our addressable market size across Coal India Limited (CIL) opencast mines and private quarries?',
  },
  {
    category: 'econ',
    categoryLabel: 'Economics & SSR',
    badge: 'Asset Protection',
    icon: '🚜',
    label: 'Protecting ₹80–120 Cr Draglines',
    prompt:
      'How does protecting ₹80-120 Cr draglines and ₹15-30 Cr shovels justify our system implementation cost?',
  },
  {
    category: 'econ',
    categoryLabel: 'Economics & SSR',
    badge: 'DGMS Mandate',
    icon: '📜',
    label: 'DGMS Safety Compliance Value',
    prompt:
      'How does this solution help mine managers comply with Directorate General of Mines Safety (DGMS) slope monitoring mandates?',
  },

  // Geotechnical & Physics
  {
    category: 'geotech',
    categoryLabel: 'Geotech & Physics',
    badge: 'Core Physics',
    icon: '📉',
    label: 'Fukuzono Inverse-Velocity Law',
    prompt:
      'What is the Fukuzono inverse-velocity equation (1/v vs time) and how does it mathematically predict time-to-failure?',
  },
  {
    category: 'geotech',
    categoryLabel: 'Geotech & Physics',
    badge: 'Site Geology',
    icon: '⛰️',
    label: 'Kusmunda 60–75° Bench Detachment',
    prompt:
      'What are the geological bench characteristics of Kusmunda Mine (60-75° faces, Korba coalfield) that cause rapid detachment?',
  },
  {
    category: 'geotech',
    categoryLabel: 'Geotech & Physics',
    badge: 'Rainfall Trigger',
    icon: '🌧️',
    label: 'Rainfall & Pore Pressure Multiplier',
    prompt:
      'How does monsoon rainfall and pore water pressure amplify rockfall detachment risk in our physics model?',
  },
  {
    category: 'geotech',
    categoryLabel: 'Geotech & Physics',
    badge: 'Rock Mass',
    icon: '📐',
    label: 'Slope Mass Rating (SMR) & Joints',
    prompt:
      'How do joint spacing, rock mass rating (RMR), and discontinuity dip angle enter our risk equation?',
  },

  // Pitch Script & Delivery
  {
    category: 'script',
    categoryLabel: 'Pitch Script',
    badge: '30-Sec Pitch',
    icon: '⚡',
    label: 'Killer 30-Second Elevator Pitch',
    prompt:
      'Explain this project in 30 seconds for a non-tech judge. Use simple words, our core innovation, and a clear headline number.',
  },
  {
    category: 'script',
    categoryLabel: 'Pitch Script',
    badge: 'Opening Hook',
    icon: '✨',
    label: 'Opening 3 Lines of 5-Min Pitch',
    prompt:
      'Write the opening 3 lines of our 5-minute SIH pitch — confident, startling, non-technical, and memorable.',
  },
  {
    category: 'script',
    categoryLabel: 'Pitch Script',
    badge: 'Closing Punch',
    icon: '🏁',
    label: 'Closing 20-Second Jury Statement',
    prompt:
      'Write a powerful 20-second closing statement that leaves judges nodding at our technical depth and real-world impact.',
  },
  {
    category: 'script',
    categoryLabel: 'Pitch Script',
    badge: 'Tough Questions',
    icon: '🤝',
    label: 'Framework for Unexpected Judge Questions',
    prompt:
      'If a judge asks an unexpected technical edge case we didn\'t test, what is the best professional response framework?',
  },
];

// Map intent key to human badge
const INTENT_MAP: Record<string, { label: string; icon: string; color: string }> = {
  'project-overview': { label: 'Project Overview', icon: '📌', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  'pitch-content': { label: 'Pitch Flow', icon: '⚡', color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  'judge-defense': { label: 'Judge Trap Counter', icon: '🛡️', color: 'bg-amber-50 text-amber-800 border-amber-200' },
  'benchmark-number': { label: 'ML Benchmark', icon: '📊', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  'glossary-term': { label: 'Glossary Term', icon: '📖', color: 'bg-purple-50 text-purple-700 border-purple-200' },
  'pitch-script': { label: 'Pitch Script', icon: '🎙️', color: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
  'project-idea': { label: 'Project Idea', icon: '💡', color: 'bg-yellow-50 text-yellow-800 border-yellow-200' },
  'data-point': { label: 'Data Point', icon: '🔢', color: 'bg-slate-50 text-slate-700 border-slate-200' },
  'general': { label: 'Grounded Answer', icon: '✨', color: 'bg-blue-50 text-blue-700 border-blue-200' },
};

// Convert inline markdown (**bold**, *italic*, `code`) to React nodes
function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /(\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`)/g;
  let last = 0;
  let i = 0;
  let m: RegExpExecArray | null;

  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      out.push(text.slice(last, m.index));
    }
    if (m[2]) {
      out.push(
        <strong key={`${keyPrefix}-b-${i}`} className="font-semibold text-[#0B1220]">
          {m[2]}
        </strong>,
      );
    } else if (m[3]) {
      out.push(
        <em key={`${keyPrefix}-i-${i}`} className="text-[#2563EB] not-italic font-medium">
          {m[3]}
        </em>,
      );
    } else if (m[4]) {
      out.push(
        <code
          key={`${keyPrefix}-c-${i}`}
          className="font-mono text-[12.5px] px-1.5 py-0.5 rounded bg-[#F2F4F8] text-[#1D4ED8] border border-[#E6E8EE]"
        >
          {m[4]}
        </code>,
      );
    }
    last = m.index + m[0].length;
    i++;
  }
  if (last < text.length) {
    out.push(text.slice(last));
  }
  return out;
}

// Convert full multi-line response into structured paragraphs, lists, and quotes
function renderAnswer(content: string) {
  const lines = content.split('\n');
  const blocks: React.ReactNode[] = [];
  let buffer: string[] = [];
  let listType: 'ul' | 'ol' | null = null;
  let listItems: string[] = [];
  let key = 0;

  const flushParagraph = () => {
    if (buffer.length === 0) return;
    const text = buffer.join(' ').trim();
    if (text) {
      blocks.push(
        <p key={`p-${key++}`} className="text-[13.5px] sm:text-[14px] text-[#0B1220] leading-[1.65]">
          {renderInline(text, `p-${key}`)}
        </p>,
      );
    }
    buffer = [];
  };

  const flushList = () => {
    if (listItems.length === 0) return;
    if (listType === 'ul') {
      blocks.push(
        <ul key={`ul-${key++}`} className="space-y-1.5 pl-0.5">
          {listItems.map((it, i) => (
            <li key={i} className="flex items-start gap-2.5 text-[13.5px] sm:text-[14px] text-[#0B1220] leading-[1.6]">
              <span className="mt-[8px] w-1.5 h-1.5 rounded-full bg-[#2563EB] flex-shrink-0" />
              <span className="flex-1">{renderInline(it, `ul-${key}-${i}`)}</span>
            </li>
          ))}
        </ul>,
      );
    } else {
      blocks.push(
        <ol key={`ol-${key++}`} className="space-y-1.5 pl-1 list-decimal list-inside text-[#0B1220]">
          {listItems.map((it, i) => (
            <li key={i} className="text-[13.5px] sm:text-[14px] leading-[1.6]">
              <span className="pl-1">{renderInline(it, `ol-${key}-${i}`)}</span>
            </li>
          ))}
        </ol>,
      );
    }
    listItems = [];
    listType = null;
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.trim() === '') {
      flushParagraph();
      flushList();
      continue;
    }
    const ulMatch = /^[-•*]\s+(.*)$/.exec(line);
    const olMatch = /^\d+\.\s+(.*)$/.exec(line);
    if (ulMatch) {
      flushParagraph();
      if (listType !== 'ul') flushList();
      listType = 'ul';
      listItems.push(ulMatch[1]);
      continue;
    }
    if (olMatch) {
      flushParagraph();
      if (listType !== 'ol') flushList();
      listType = 'ol';
      listItems.push(olMatch[1]);
      continue;
    }
    flushList();
    buffer.push(line);
  }
  flushParagraph();
  flushList();

  return <div className="space-y-3">{blocks}</div>;
}

// Aria Avatar
function AriaAvatar({ size = 32 }: { size?: number }) {
  return (
    <div
      className="flex-shrink-0 rounded-full flex items-center justify-center font-bold text-white relative shadow-sm"
      style={{
        width: size,
        height: size,
        background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
        fontSize: size * 0.44,
        letterSpacing: '-0.02em',
      }}
      aria-hidden
    >
      <span>A</span>
      <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 ring-2 ring-white" />
    </div>
  );
}

// User Avatar
function UserAvatar({ size = 32 }: { size?: number }) {
  return (
    <div
      className="flex-shrink-0 rounded-full flex items-center justify-center font-semibold text-[#0B1220] bg-[#F2F4F8] border border-[#E6E8EE] shadow-xs"
      style={{ width: size, height: size, fontSize: size * 0.38 }}
      aria-hidden
    >
      You
    </div>
  );
}

// 3-dot pulse loader
function LoadingDots() {
  return (
    <div className="flex items-center gap-2 py-1">
      <div className="flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-2 h-2 rounded-full bg-[#2563EB] animate-bounce"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </div>
      <span className="text-[12px] font-medium text-[#5B6472]">
        Searching pitch knowledge base & synthesizing…
      </span>
    </div>
  );
}

// Source Citation Card
function SourceChip({ s, idx }: { s: RetrievedSource; idx: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-[#E6E8EE] bg-[#FBFBFD] overflow-hidden transition hover:border-[#2563EB]/40">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full text-left flex items-start gap-2.5 px-3 py-2 cursor-pointer transition select-none"
      >
        <span className="mt-0.5 text-[10px] font-mono font-bold uppercase tracking-[0.16em] text-[#2563EB] bg-[#EFF4FF] border border-[#D7E2F8] px-1.5 py-0.5 rounded">
          S{idx + 1}
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[12px] font-semibold text-[#0B1220] truncate">
            {s.title}
          </div>
          <div className="text-[10.5px] text-[#8A93A1] truncate">
            {s.tab} · {s.section}
          </div>
        </div>
        <svg
          className={`w-3.5 h-3.5 text-[#8A93A1] transition-transform duration-200 mt-1 flex-shrink-0 ${
            open ? 'rotate-90 text-[#2563EB]' : ''
          }`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m9 18 6-6-6-6" />
        </svg>
      </button>

      {open && (
        <div className="px-3 pb-3 pt-2 border-t border-[#E6E8EE] bg-white text-[12px] text-[#5B6472] leading-relaxed whitespace-pre-wrap animate-[fadeIn_150ms_ease-out]">
          <p>{s.body}</p>
          {s.meta && (
            <div className="mt-2 text-[10.5px] font-mono text-[#8A93A1]">
              Ref: {s.meta}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Single Message Bubble
function MessageBubble({
  role,
  content,
  sources,
  intent,
  isStreaming,
}: {
  role: 'user' | 'assistant';
  content: string;
  sources?: RetrievedSource[];
  intent?: string | null;
  isStreaming?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(content).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      });
    }
  };

  if (role === 'user') {
    return (
      <div className="flex items-start gap-2.5 justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-xs bg-[#0B1220] text-white px-4 py-3 text-[13.5px] sm:text-[14px] leading-relaxed shadow-sm">
          {content}
        </div>
        <UserAvatar size={28} />
      </div>
    );
  }

  const intentInfo = intent ? INTENT_MAP[intent] || INTENT_MAP['general'] : null;

  return (
    <div className="flex items-start gap-2.5 justify-start">
      <AriaAvatar size={28} />
      <div className="max-w-[90%] min-w-0 space-y-2">
        <div className="rounded-2xl rounded-tl-xs bg-white border border-[#E6E8EE] px-4 sm:px-5 py-4 shadow-sm shadow-slate-900/[0.02]">
          {/* Intent Tag */}
          {intentInfo && !isStreaming && (
            <div className="mb-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-[0.16em] px-2 py-0.5 rounded-md border font-semibold">
              <span className={intentInfo.color}>
                {intentInfo.icon} {intentInfo.label}
              </span>
            </div>
          )}

          {isStreaming && !content ? (
            <LoadingDots />
          ) : (
            renderAnswer(content)
          )}

          {/* Sources Section */}
          {sources && sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-[#F2F4F8] space-y-2">
              <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">
                <span>Grounded Sources ({sources.length})</span>
                <span className="text-[#2563EB]">SIH25071 KB</span>
              </div>
              <div className="grid grid-cols-1 gap-2">
                {sources.map((s, i) => (
                  <SourceChip key={i} s={s} idx={i} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Message Actions */}
        {!isStreaming && content && (
          <div className="flex items-center justify-between px-1 text-[11px] text-[#8A93A1]">
            <span>Grounded in project data</span>
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1 text-[11px] font-medium text-[#5B6472] hover:text-[#2563EB] transition px-2 py-0.5 rounded hover:bg-[#F2F4F8]"
              title="Copy answer"
            >
              {copied ? (
                <>
                  <svg className="w-3.5 h-3.5 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span className="text-emerald-600 font-semibold">Copied</span>
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                    <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                  </svg>
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Knowledge Base Stats Sheet
function KnowledgeInfoSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <div className="border-b border-[#E6E8EE] bg-[#FBFBFD] px-5 py-4 animate-[fadeIn_150ms_ease-out] text-[#0B1220]">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#2563EB]" />
          <span className="text-[12px] font-semibold text-[#0B1220]">
            SIH25071 Master Knowledge Base
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-[11px] text-[#5B6472] hover:text-[#0B1220] font-medium"
        >
          Hide ✕
        </button>
      </div>

      <p className="text-[12px] text-[#5B6472] leading-relaxed mb-3">
        Aria is grounded in every Q&A, judge defense, ML benchmark, and pitch teleprompter segment for Kusmunda opencast mine.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11.5px]">
        {[
          ['50+', 'Curated Q&As', '📚'],
          ['15', 'Judge Defenses', '🛡️'],
          ['3', 'ML Benchmark Models', '📊'],
          ['16', 'Glossary Terms', '📖'],
          ['4', 'Teleprompter Segments', '🎙️'],
          ['100%', 'Grounded Citations', '🎯'],
        ].map(([val, title, icon]) => (
          <div
            key={title}
            className="rounded-lg border border-[#E6E8EE] bg-white p-2 flex items-center justify-between"
          >
            <div className="flex items-center gap-1.5 truncate">
              <span>{icon}</span>
              <span className="text-[#5B6472] truncate">{title}</span>
            </div>
            <span className="font-mono font-bold text-[#2563EB] ml-1.5">{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Main AriaTab Component
// ============================================================================

export default function AriaTab({ onClose }: { onClose?: () => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSources, setLastSources] = useState<RetrievedSource[]>([]);
  const [lastIntent, setLastIntent] = useState<string | null>(null);
  const [showInfo, setShowInfo] = useState(false);
  const [selectedTopic, setSelectedTopic] = useState<TopicCategory>('all');

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  // Auto-scroll to bottom on update
  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages, busy]);

  // Auto-focus input
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Filtered prompt questions based on active topic tag
  const filteredPrompts = useMemo(() => {
    if (selectedTopic === 'all') {
      // Pick top-priority representative question from each domain
      return [
        TOP_PRIORITY_PROMPTS.find((p) => p.label.includes('30-Second Elevator'))!,
        TOP_PRIORITY_PROMPTS.find((p) => p.label.includes('Synthetic'))!,
        TOP_PRIORITY_PROMPTS.find((p) => p.label.includes('Model Accuracy'))!,
        TOP_PRIORITY_PROMPTS.find((p) => p.label.includes('Cost of SSR'))!,
        TOP_PRIORITY_PROMPTS.find((p) => p.label.includes('End-to-End Pipeline'))!,
        TOP_PRIORITY_PROMPTS.find((p) => p.label.includes('Fukuzono'))!,
      ].filter(Boolean);
    }
    return TOP_PRIORITY_PROMPTS.filter((p) => p.category === selectedTopic);
  }, [selectedTopic]);

  const canSend = useMemo(
    () => input.trim().length > 0 && !busy,
    [input, busy],
  );

  async function send(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;

    setError(null);
    setInput('');

    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = '44px';
    }

    const nextHistory: ChatMessage[] = [
      ...messages,
      { role: 'user', content: msg },
    ];
    setMessages(nextHistory);
    setBusy(true);

    try {
      const res = await fetch('/api/rag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msg,
          history: messages,
        }),
      });

      const json = (await res.json()) as RagApiResponse | RagApiError;
      if (!res.ok) {
        const e = json as RagApiError;
        throw new Error(e.error || `Request failed (${res.status})`);
      }
      const ok = json as RagApiResponse;
      setMessages((cur) => [...cur, { role: 'assistant', content: ok.answer }]);
      setLastSources(ok.sources || []);
      setLastIntent(ok.intent || null);
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e);
      setError(errMsg);
      setMessages((cur) => cur.slice(0, -1));
    } finally {
      setBusy(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function clearChat() {
    setMessages([]);
    setError(null);
    setLastSources([]);
    setLastIntent(null);
    inputRef.current?.focus();
  }

  return (
    <div className="flex flex-col h-full w-full bg-white overflow-hidden select-text">
      {/* Header bar */}
      <header className="px-5 py-3.5 border-b border-[#E6E8EE] flex items-center justify-between gap-3 bg-white flex-shrink-0 z-10">
        <div className="flex items-center gap-3">
          <AriaAvatar size={34} />
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-[14.5px] font-bold text-[#0B1220] leading-tight">
                Aria
              </h2>
              <span className="text-[9.5px] font-mono font-semibold uppercase tracking-[0.16em] text-[#2563EB] bg-[#EFF4FF] border border-[#D7E2F8] rounded-full px-2 py-0.5">
                AI Pitch Partner
              </span>
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[11px] text-[#5B6472]">
                SIH 2026 Grounded Assistant
              </span>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setShowInfo(!showInfo)}
            title="What Aria Knows"
            aria-label="Toggle Knowledge Base Info"
            className={`text-[11.5px] font-medium px-2.5 py-1.5 rounded-full border transition flex items-center gap-1.5 ${
              showInfo
                ? 'bg-[#EFF4FF] text-[#2563EB] border-[#D7E2F8]'
                : 'bg-white text-[#5B6472] border-[#E6E8EE] hover:text-[#0B1220] hover:border-[#2563EB]'
            }`}
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            <span className="hidden sm:inline">Index</span>
          </button>

          {messages.length > 0 && (
            <button
              type="button"
              onClick={clearChat}
              title="Clear chat"
              className="text-[11.5px] font-medium text-[#5B6472] hover:text-rose-600 px-2.5 py-1.5 rounded-full border border-[#E6E8EE] hover:border-rose-300 hover:bg-rose-50 transition"
            >
              Clear
            </button>
          )}

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              title="Close chat"
              aria-label="Close chat"
              className="w-8 h-8 rounded-full text-[#5B6472] hover:text-[#0B1220] hover:bg-[#F2F4F8] transition flex items-center justify-center ml-1"
            >
              <svg
                viewBox="0 0 24 24"
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
              >
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </header>

      {/* Expandable Knowledge Base sheet */}
      <KnowledgeInfoSheet open={showInfo} onClose={() => setShowInfo(false)} />

      {/* Topic Filter Pill Tags Bar */}
      <div className="px-4 py-2.5 border-b border-[#E6E8EE] bg-white flex-shrink-0 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
        {TOPIC_FILTERS.map((t) => {
          const active = selectedTopic === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setSelectedTopic(t.id)}
              className={`flex-shrink-0 flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-full transition ${
                active
                  ? 'bg-[#0B1220] text-white shadow-xs'
                  : 'bg-[#F8FAFC] text-[#5B6472] border border-[#E6E8EE] hover:border-[#2563EB] hover:text-[#0B1220]'
              }`}
            >
              <span className="text-[12px]">{t.icon}</span>
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main chat messages feed */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto overflow-x-hidden px-4 sm:px-5 py-5 space-y-4 aria-chat-feed"
        style={{ backgroundColor: '#FBFBFD' }}
      >
        {messages.length === 0 && (
          <div className="space-y-4 animate-[fadeIn_200ms_ease-out]">
            {/* Welcome banner */}
            <div className="rounded-2xl bg-gradient-to-b from-[#EFF4FF]/80 to-white border border-[#D7E2F8] p-4 sm:p-5 shadow-sm">
              <div className="flex items-start gap-3">
                <AriaAvatar size={32} />
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-[14px] font-bold text-[#0B1220]">
                    Rehearse your SIH pitch with instant answers
                  </h3>
                  <p className="text-[13px] text-[#5B6472] leading-relaxed">
                    Filter by topic tags above to explore high-priority questions, benchmark stats, and winning judge trap counter-punches.
                  </p>
                </div>
              </div>
            </div>

            {/* Topic-Specific Suggested Questions */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between px-1">
                <span className="text-[10.5px] font-mono uppercase tracking-[0.18em] text-[#8A93A1]">
                  Top Questions · {TOPIC_FILTERS.find((t) => t.id === selectedTopic)?.label}
                </span>
                <span className="text-[11px] text-[#2563EB] font-medium">
                  {filteredPrompts.length} questions
                </span>
              </div>

              <div className="grid grid-cols-1 gap-2">
                {filteredPrompts.map((q) => (
                  <button
                    key={q.label}
                    type="button"
                    onClick={() => send(q.prompt)}
                    disabled={busy}
                    className="w-full text-left p-3 rounded-xl bg-white border border-[#E6E8EE] hover:border-[#2563EB] hover:shadow-sm text-[#0B1220] transition group disabled:opacity-50 disabled:cursor-not-allowed flex items-start gap-3"
                  >
                    <span className="text-[16px] mt-0.5 flex-shrink-0">{q.icon}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[10px] font-mono font-bold uppercase tracking-[0.14em] text-[#2563EB] bg-[#EFF4FF] border border-[#D7E2F8] px-1.5 py-0.5 rounded">
                          {q.badge}
                        </span>
                        <h4 className="text-[13px] font-semibold text-[#0B1220] group-hover:text-[#2563EB] transition truncate">
                          {q.label}
                        </h4>
                      </div>
                      <p className="text-[12px] text-[#5B6472] leading-relaxed line-clamp-2">
                        {q.prompt}
                      </p>
                    </div>
                    <svg
                      className="w-4 h-4 text-[#8A93A1] group-hover:text-[#2563EB] group-hover:translate-x-0.5 transition-all mt-1 flex-shrink-0"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Message stream */}
        {messages.map((m, i) => (
          <MessageBubble
            key={i}
            role={m.role}
            content={m.content}
            sources={
              m.role === 'assistant' && i === messages.length - 1 && !busy
                ? lastSources
                : undefined
            }
            intent={
              m.role === 'assistant' && i === messages.length - 1
                ? lastIntent
                : null
            }
          />
        ))}

        {busy && (
          <MessageBubble
            role="assistant"
            content=""
            isStreaming
          />
        )}

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-[13px] text-rose-700 flex items-start gap-2.5">
            <svg className="w-4 h-4 text-rose-600 mt-0.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div className="flex-1">
              <strong>Couldn&rsquo;t reach Aria:</strong> {error}
              <div className="mt-1.5">
                <button
                  type="button"
                  onClick={() => send(messages[messages.length - 1]?.content)}
                  className="text-[11.5px] font-semibold text-rose-800 hover:underline"
                >
                  Retry question ↺
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Dock */}
      <footer className="border-t border-[#E6E8EE] px-4 py-3 bg-white flex-shrink-0 z-10">
        <div className="relative flex items-end gap-2 bg-[#F8FAFC] border border-[#E6E8EE] focus-within:border-[#2563EB] focus-within:bg-white focus-within:ring-2 focus-within:ring-[#2563EB]/15 rounded-2xl p-1.5 transition-all">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Aria anything about the pitch, radar cost, ML recall..."
            rows={1}
            disabled={busy}
            className="flex-1 resize-none px-3 py-2 text-[13.5px] sm:text-[14px] text-[#0B1220] bg-transparent outline-none disabled:opacity-50 max-h-32 min-h-[40px] leading-relaxed custom-scrollbar"
            onInput={(e) => {
              const t = e.currentTarget;
              t.style.height = 'auto';
              t.style.height = Math.min(t.scrollHeight, 120) + 'px';
            }}
          />
          <button
            type="button"
            onClick={() => send()}
            disabled={!canSend}
            title="Send message"
            aria-label="Send message"
            className="flex-shrink-0 w-9 h-9 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] disabled:bg-[#E6E8EE] disabled:text-[#8A93A1] text-white flex items-center justify-center transition shadow-xs disabled:cursor-not-allowed mb-0.5"
          >
            {busy ? (
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                <path d="M12 2a10 10 0 0 1 10 10" />
              </svg>
            ) : (
              <svg
                viewBox="0 0 24 24"
                className="w-4 h-4 translate-x-px"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m22 2-7 20-4-9-9-4Z" />
                <path d="M22 2 11 13" />
              </svg>
            )}
          </button>
        </div>

        <div className="mt-2 flex items-center justify-between text-[10.5px] text-[#8A93A1] px-1">
          <span>
            <strong className="text-[#5B6472]">↵ Enter</strong> to send · <strong className="text-[#5B6472]">Shift+↵</strong> new line
          </span>
          <span className="hidden sm:inline">Grounded in SIH25071 facts</span>
        </div>
      </footer>

      {/* Scoped clean styles for custom scrollbar & no-scrollbar */}
      <style jsx global>{`
        .aria-chat-feed::-webkit-scrollbar {
          width: 5px;
        }
        .aria-chat-feed::-webkit-scrollbar-track {
          background: transparent;
        }
        .aria-chat-feed::-webkit-scrollbar-thumb {
          background: #D7E2F8;
          border-radius: 9999px;
        }
        .aria-chat-feed::-webkit-scrollbar-thumb:hover {
          background: #2563EB;
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #E6E8EE;
          border-radius: 9999px;
        }
        .no-scrollbar::-webkit-scrollbar {
          display: none;
        }
        .no-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
    </div>
  );
}
