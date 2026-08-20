// ============================================================================
// JSON-based RAG retriever for the Pitch Companion knowledge base.
// Lightweight keyword + tag scoring. No vector DB, no embeddings — just
// deterministic scoring that runs on the server in <5ms for ~100 chunks.
// ============================================================================

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
  type PitchItem,
  type Flashcard,
  type GlossaryTerm,
  type BenchmarkModel,
  type TeleprompterSegment,
} from '../../pitch/data';

// ----------------------------------------------------------------------------
// Types
// ----------------------------------------------------------------------------

export type RetrievedSource = {
  /** Where this chunk lives in the page UI. */
  tab:
    | 'Pitch Flow'
    | 'Judge Traps'
    | 'ML Benchmark'
    | 'Teleprompter'
    | 'Glossary'
    | 'Project Info';
  /** Which chapter / section inside the tab. */
  section: string;
  /** Human-readable title shown to the user as a citation. */
  title: string;
  /** Short text body fed to the LLM. */
  body: string;
  /** Optional structured payload (tags, flashcard trap/counter, etc.). */
  meta?: string;
  /** Raw relevance score (higher = better). */
  score: number;
};

export type RetrievedContext = {
  sources: RetrievedSource[];
  /** Concatenated context block ready to inject into the system prompt. */
  contextBlock: string;
  /** Top-intent guess: what kind of question the user asked. */
  intent: Intent;
};

export type Intent =
  | 'project-overview'
  | 'pitch-content'
  | 'judge-defense'
  | 'benchmark-number'
  | 'glossary-term'
  | 'pitch-script'
  | 'project-idea'
  | 'data-point'
  | 'general';

// ----------------------------------------------------------------------------
// Project meta — short, hand-curated, covers questions outside the Q&A
// (e.g. "what is the project?", "who are we?", "give me a project idea").
// ----------------------------------------------------------------------------

const PROJECT_META: RetrievedSource[] = [
  {
    tab: 'Project Info',
    section: 'About',
    title: 'Project: AI-Powered Rockfall Early Warning System',
    body:
      'SIH 2026 Problem Statement SIH25071, issued by the Ministry of Mines. ' +
      'A real-time slope-stability monitoring system for opencast coal mines, ' +
      'anchored to Kusmunda Mine (SECL, Korba Coalfield, Chhattisgarh). ' +
      'Fuses four data streams — on-site geotech sensors, Sentinel-1 SAR, ' +
      'Copernicus DEM, and Open-Meteo rainfall — under the Fukuzono 1985 ' +
      'inverse-velocity physics, and ships a 10-feature XGBoost champion ' +
      'model with 100% Evacuation Recall on the held-out test set.',
    score: 0,
  },
  {
    tab: 'Project Info',
    section: 'Why it matters',
    title: 'Why this project (human + business case)',
    body:
      'Slope failure is a top-3 fatal incident in Indian opencast mining. ' +
      'A single collapse shuts a mine for ~30 days, costing ₹150–450 Cr in lost ' +
      'production plus ₹50–100 Cr in equipment. Manual visual rounds have an ' +
      '8-hour blind spot. The industry gold standard (Slope Stability Radar) ' +
      'costs ₹2–4 Cr per unit and covers only 60–80% of a pit. Our system ' +
      'covers the 20–40% shadow zones at 5–10% of the cost.',
    score: 0,
  },
  {
    tab: 'Project Info',
    section: 'Team delivery',
    title: 'How the system was built (8-day solo sprint)',
    body:
      'Delivered solo across 16 phases: problem scoping, GEE geospatial ingestion, ' +
      'physics-informed synthetic data, XGBoost + RandomForest training, SHAP ' +
      'explainability, v2 label fix, v2b/v2c isolation tests, GRU benchmark, ' +
      'FastAPI + Pydantic backend, WebSocket /ws/feed, Next.js 16 + MapLibre 3D ' +
      'dashboard, ONNX edge export for Raspberry Pi / Jetson, and Render + Vercel ' +
      'deploy. SDG alignment: 8, 9, 11, 13.',
    score: 0,
  },
  {
    tab: 'Project Info',
    section: 'Suggested project extensions',
    title: 'Pitch-friendly ideas to expand the project',
    body:
      'Realistic extensions a teammate can propose during Q&A: ' +
      '(1) UWB or BLE worker-location heatmap fused with risk zones; ' +
      '(2) WhatsApp Business API alerts instead of SMS-only; ' +
      '(3) Multi-mine federated learning across CIL subsidiaries; ' +
      '(4) Auto-generated daily shift report for DGMS audit; ' +
      '(5) Acoustic emission sensor add-on to detect pre-fracture microseismic; ' +
      '(6) Drone-based photogrammetry refresh of the DEM every 7 days; ' +
      '(7) Public-facing risk dashboard for surrounding villages (PMKKKY).',
    score: 0,
  },
];

// ----------------------------------------------------------------------------
// Tokenisation
// ----------------------------------------------------------------------------

const STOP_WORDS = new Set([
  'a', 'an', 'and', 'are', 'as', 'at', 'be', 'but', 'by', 'do', 'does',
  'for', 'from', 'has', 'have', 'how', 'i', 'in', 'is', 'it', 'its', 'me',
  'my', 'of', 'on', 'or', 'our', 'so', 'such', 'that', 'the', 'their',
  'them', 'then', 'there', 'these', 'they', 'this', 'to', 'us', 'was',
  'we', 'what', 'when', 'where', 'which', 'who', 'why', 'will', 'with',
  'you', 'your', 'can', 'should', 'would', 'could', 'about', 'into',
  'over', 'than', 'also', 'any', 'all', 'one', 'two', 'three',
]);

function tokenize(s: string): string[] {
  return (s || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s\-]/g, ' ')
    .split(/\s+/)
    .map((t) => t.trim())
    .filter((t) => t.length >= 2 && !STOP_WORDS.has(t));
}

// ----------------------------------------------------------------------------
// Intent classification — cheap rule-based, used to bias retrieval
// ----------------------------------------------------------------------------

function classifyIntent(q: string): Intent {
  const ql = q.toLowerCase();

  if (/\b(judge|trap|do not say|don\u2019t say|counter|defend|defence|defense|objection|challenge)\b/.test(ql))
    return 'judge-defense';
  if (/\b(accuracy|recall|precision|f1|benchmark|gru|xgboost|randomforest|metric|97|98|197|missed)\b/.test(ql))
    return 'benchmark-number';
  if (/^(what is|define|meaning of|explain term|glossary)\b/.test(ql))
    return 'glossary-term';
  if (/\b(script|teleprompter|say this|present|presenter|minute|rehearse|pitch script)\b/.test(ql))
    return 'pitch-script';
  if (/\b(idea|extension|future|add[- ]?on|enhance|expand|suggest|propose|next step|scope)\b/.test(ql))
    return 'project-idea';
  if (/\b(stat|number|figure|metric|cost|price|crore|lakh|percent|%|how many|how much|amount)\b/.test(ql))
    return 'data-point';
  if (/\b(what is this project|about the project|tell me about|overview|summary|what do you do|what is sih|sih25071|rockfall|landslide)\b/.test(ql))
    return 'project-overview';
  return 'pitch-content';
}

// ----------------------------------------------------------------------------
// Scoring
// ----------------------------------------------------------------------------

const SECTION_TITLES: Record<string, string> = {
  '01': 'Chapter 01 — Problem & Market Deep-Dive',
  '02': 'Chapter 02 — Technical Architecture',
  '03': 'Chapter 03 — Machine Learning & Data Science',
  '04': 'Chapter 04 — Deployment, Edge & Scaling',
  '05': 'Chapter 05 — Innovation, Impact & SDGs',
  '07': 'Chapter 07 — Deep Learning Benchmark (GRU vs Trees)',
};

function scoreField(queryTokens: string[], text: string, weight: number): number {
  if (!text) return 0;
  const textTokens = new Set(tokenize(text));
  let s = 0;
  for (const t of queryTokens) {
    if (textTokens.has(t)) s += weight;
    // partial: handle simple plural / stem by checking substring matches
    else {
      for (const tt of textTokens) {
        if (tt.length > 4 && (tt.startsWith(t) || t.startsWith(tt))) {
          s += weight * 0.4;
          break;
        }
      }
    }
  }
  return s;
}

function tagsBonus(queryTokens: string[], tags?: string[]): number {
  if (!tags || tags.length === 0) return 0;
  let s = 0;
  for (const tag of tags) {
    if (queryTokens.includes(tag.toLowerCase())) s += 2.5;
  }
  return s;
}

function scorePitchItem(item: PitchItem, sectionKey: string, queryTokens: string[]): RetrievedSource {
  const qScore = scoreField(queryTokens, item.q, 3);
  const shortScore = scoreField(queryTokens, item.short, 1.2);
  const fullScore = scoreField(queryTokens, item.full, 1);
  const plainScore = scoreField(queryTokens, item.plain || '', 0.8);
  const tagScore = tagsBonus(queryTokens, item.tags);
  const score = qScore + shortScore + fullScore + plainScore + tagScore;
  return {
    tab: 'Pitch Flow',
    section: SECTION_TITLES[sectionKey] || `Chapter ${sectionKey}`,
    title: item.q,
    body: `${item.short}\n\n${item.full}${item.plain ? `\n\n(Plain English: ${item.plain})` : ''}`,
    meta: item.tags?.length ? `tags: ${item.tags.slice(0, 6).join(', ')}` : undefined,
    score,
  };
}

function scoreFlashcard(card: Flashcard, queryTokens: string[]): RetrievedSource {
  const qScore = scoreField(queryTokens, card.q, 3);
  const trapScore = scoreField(queryTokens, card.trap, 1.2);
  const counterScore = scoreField(queryTokens, card.counter, 1.2);
  const dnsScore = scoreField(queryTokens, (card.doNotSay || []).join(' '), 1);
  const score = qScore + trapScore + counterScore + dnsScore;
  return {
    tab: 'Judge Traps',
    section: 'Chapter 06 — Judge Defense & Flashcard Arena',
    title: card.q,
    body: `TRAP: ${card.trap}\n\nCOUNTER: ${card.counter}${
      card.doNotSay?.length ? `\n\nDO NOT SAY: ${card.doNotSay.join(' | ')}` : ''
    }`,
    score,
  };
}

function scoreGlossary(term: GlossaryTerm, queryTokens: string[]): RetrievedSource {
  const termScore = scoreField(queryTokens, term.term, 4);
  const plainScore = scoreField(queryTokens, term.plain, 1.5);
  const detailScore = scoreField(queryTokens, term.detail || '', 1);
  const score = termScore + plainScore + detailScore;
  return {
    tab: 'Glossary',
    section: 'LEX — Non-Tech Glossary',
    title: term.term,
    body: `${term.plain}${term.detail ? `\n\n${term.detail}` : ''}`,
    score,
  };
}

function scoreBenchmark(queryTokens: string[]): RetrievedSource[] {
  const out: RetrievedSource[] = [];
  for (const m of benchmarkModels) {
    const score =
      scoreField(queryTokens, m.name, 3) +
      scoreField(queryTokens, m.note, 1.5) +
      scoreField(queryTokens, `${m.precision} ${m.recall} ${m.f1}`, 0.5);
    out.push({
      tab: 'ML Benchmark',
      section: 'BENCH — ML Performance & Model Benchmark',
      title: `${m.name} (${m.tone})`,
      body:
        `${m.name} on 1,136 held-out rows / 197 Evacuations: ` +
        `Precision ${(m.precision * 100).toFixed(2)}%, ` +
        `Recall ${(m.recall * 100).toFixed(2)}%, ` +
        `F1 ${(m.f1 * 100).toFixed(2)}%. ` +
        `Missed evacuations: ${m.missed} / ${m.totalEvac}. ` +
        `${m.note}`,
      meta: `tone: ${m.tone}`,
      score,
    });
  }
  return out;
}

function scoreTeleprompter(seg: TeleprompterSegment, queryTokens: string[]): RetrievedSource {
  const titleScore = scoreField(queryTokens, seg.title, 2.5);
  const pointsScore = scoreField(queryTokens, seg.points.join(' '), 1.2);
  return {
    tab: 'Teleprompter',
    section: `TELE — ${seg.minute}`,
    title: seg.title,
    body: seg.points.map((p) => `• ${p}`).join('\n'),
    score: titleScore + pointsScore,
  };
}

// ----------------------------------------------------------------------------
// Public retriever
// ----------------------------------------------------------------------------

export function retrieve(query: string, k = 6): RetrievedContext {
  const q = (query || '').trim();
  const intent = classifyIntent(q);
  const queryTokens = tokenize(q);

  // If the query is empty or just stop words, fall back to project meta.
  if (queryTokens.length === 0) {
    return {
      sources: PROJECT_META.slice(0, 3),
      contextBlock: PROJECT_META.slice(0, 3)
        .map((s) => `[${s.tab} → ${s.title}]\n${s.body}`)
        .join('\n\n---\n\n'),
      intent: 'project-overview',
    };
  }

  const scored: RetrievedSource[] = [];

  // Pitch items
  const allPitchSections: Array<[string, PitchItem[]]> = [
    ['01', section01],
    ['02', section02],
    ['03', section03],
    ['04', section04],
    ['05', section05],
    ['07', section07],
  ];
  for (const [key, items] of allPitchSections) {
    for (const it of items) scored.push(scorePitchItem(it, key, queryTokens));
  }
  // Flashcards
  for (const c of section06) scored.push(scoreFlashcard(c, queryTokens));
  // Glossary
  for (const t of glossary) scored.push(scoreGlossary(t, queryTokens));
  // Benchmark models
  scored.push(...scoreBenchmark(queryTokens));
  // Teleprompter
  for (const seg of teleprompter) scored.push(scoreTeleprompter(seg, queryTokens));
  // Project meta
  for (const p of PROJECT_META) {
    scored.push({
      ...p,
      score:
        scoreField(queryTokens, p.title, 2) +
        scoreField(queryTokens, p.body, 1),
    });
  }

  scored.sort((a, b) => b.score - a.score);

  // Drop zero-score noise unless we have very few hits.
  let top = scored.filter((s) => s.score > 0);
  if (top.length < 3) {
    // Fall back to project meta + best-glossary so the LLM still has a footing.
    const fillers = PROJECT_META.slice(0, 3);
    const bestGlossary = scored
      .filter((s) => s.tab === 'Glossary')
      .slice(0, 2);
    top = [...top, ...bestGlossary, ...fillers];
  }

  // Intent-aware re-ranking: if the user asked about a judge trap, prefer
  // Judge Traps; if they asked a benchmark number, prefer ML Benchmark; etc.
  const intentBias: Partial<Record<Intent, number>> = {
    'judge-defense': 0,
    'benchmark-number': 0,
    'glossary-term': 0,
    'pitch-script': 0,
    'project-idea': 0,
  };
  switch (intent) {
    case 'judge-defense':
      intentBias['judge-defense'] = 1.0;
      break;
    case 'benchmark-number':
      intentBias['benchmark-number'] = 1.0;
      break;
    case 'glossary-term':
      intentBias['glossary-term'] = 0.8;
      break;
    case 'pitch-script':
      intentBias['pitch-script'] = 0.8;
      break;
    case 'project-idea':
      intentBias['project-idea'] = 0.5;
      break;
  }

  const biased = top.map((s) => {
    let bonus = 0;
    if (intent === 'judge-defense' && s.tab === 'Judge Traps') bonus += 5;
    if (intent === 'benchmark-number' && s.tab === 'ML Benchmark') bonus += 5;
    if (intent === 'glossary-term' && s.tab === 'Glossary') bonus += 5;
    if (intent === 'pitch-script' && s.tab === 'Teleprompter') bonus += 5;
    if (intent === 'project-idea' && s.tab === 'Project Info') bonus += 5;
    if (intent === 'project-overview' && s.tab === 'Project Info') bonus += 4;
    if (intent === 'pitch-content' && s.tab === 'Pitch Flow') bonus += 1;
    return { ...s, score: s.score + bonus };
  });

  biased.sort((a, b) => b.score - a.score);

  const sources = biased.slice(0, k);

  const contextBlock = sources
    .map(
      (s, i) =>
        `[Source ${i + 1} — ${s.tab} → ${s.section} → ${s.title}]\n${s.body}`,
    )
    .join('\n\n---\n\n');

  return { sources, contextBlock, intent };
}
