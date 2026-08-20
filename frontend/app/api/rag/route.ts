// ============================================================================
// POST /api/rag
// JSON-based RAG endpoint for the pitch page.
// - Retrieves top-k chunks from the pitch knowledge base
// - Calls Groq llama-3.3-70b-versatile with strict system prompt
// - Returns { answer, sources, intent }
// ============================================================================

import { NextRequest, NextResponse } from 'next/server';
import { retrieve, type RetrievedSource } from './retriever';
import { ARIA_SYSTEM_PROMPT, ARIA_SYSTEM_PROMPT_SHORT } from './systemPrompt';

// Force dynamic so this route never gets cached at build time.
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

// ----------------------------------------------------------------------------
// Types
// ----------------------------------------------------------------------------

type ChatMessage = { role: 'user' | 'assistant'; content: string };

type RagRequest = {
  message: string;
  history?: ChatMessage[];
};

type RagResponse = {
  answer: string;
  sources: RetrievedSource[];
  intent: string;
  model: string;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
};

type RagError = {
  error: string;
  detail?: string;
};

const GROQ_ENDPOINT = 'https://api.groq.com/openai/v1/chat/completions';
// Default to the best model actually available on this Groq account.
// The user originally asked for `llama-3.3-70b-versatile` but this API key
// does not have access to it (only the prompt-guard variants show up in /v1/models).
// `openai/gpt-oss-120b` is OpenAI's open-weights 120B model hosted on Groq —
// same quality tier, available on the same key, and ideal for grounded RAG.
// Override by setting GROQ_MODEL in .env.local.
const GROQ_MODEL =
  process.env.GROQ_MODEL || 'openai/gpt-oss-120b';

// Hard ceiling on conversation history we send to the model (keep cost sane).
const MAX_HISTORY_MESSAGES = 8;
// Cap total chars of history we forward to avoid token bloat.
const MAX_HISTORY_CHARS = 6000;

// `openai/gpt-oss-120b` only accepts the `developer` system role — not
// `system`. Other Groq models use `system`. Detect and switch automatically.
function systemRoleFor(model: string): 'system' | 'developer' {
  return model.startsWith('openai/') ? 'developer' : 'system';
}

// ----------------------------------------------------------------------------
// Handler
// ----------------------------------------------------------------------------

export async function POST(req: NextRequest) {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    return NextResponse.json<RagError>(
      {
        error: 'GROQ_API_KEY is not configured on the server.',
        detail:
          'Set GROQ_API_KEY in frontend/.env.local and restart `next dev`.',
      },
      { status: 500 },
    );
  }

  let body: RagRequest;
  try {
    body = (await req.json()) as RagRequest;
  } catch {
    return NextResponse.json<RagError>(
      { error: 'Invalid JSON body.' },
      { status: 400 },
    );
  }

  const userMessage = (body?.message || '').trim();
  if (!userMessage) {
    return NextResponse.json<RagError>(
      { error: '`message` is required and must be a non-empty string.' },
      { status: 400 },
    );
  }
  if (userMessage.length > 2000) {
    return NextResponse.json<RagError>(
      { error: '`message` is too long (max 2000 characters).' },
      { status: 400 },
    );
  }

  const history = Array.isArray(body.history) ? body.history : [];

  // 1. Retrieve
  const { sources, contextBlock, intent } = retrieve(userMessage, 6);

  // 2. Build the system prompt (full version on first turn, short on follow-ups).
  const isFirstTurn = history.length === 0;
  const baseSystem = isFirstTurn ? ARIA_SYSTEM_PROMPT : ARIA_SYSTEM_PROMPT_SHORT;
  const systemContent = isFirstTurn
    ? `${baseSystem}\n\n────────────────────────────────────────\nRETRIEVED CONTEXT\n────────────────────────────────────────\n${contextBlock}`
    : `${baseSystem}\n\n────────────────────────────────────────\nRETRIEVED CONTEXT (this turn)\n────────────────────────────────────────\n${contextBlock}`;

  // 3. Build the messages array. Trim history if it gets too long.
  const trimmedHistory = trimHistory(history);
  const sysRole = systemRoleFor(GROQ_MODEL);
  const messages: Array<{ role: 'system' | 'developer' | 'user' | 'assistant'; content: string }> = [
    { role: sysRole, content: systemContent },
    ...trimmedHistory,
    { role: 'user', content: userMessage },
  ];

  // 4. Call Groq.
  let groqRes: Response;
  try {
    groqRes = await fetch(GROQ_ENDPOINT, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: GROQ_MODEL,
        messages,
        temperature: 0.4,
        top_p: 0.95,
        max_tokens: 900,
        stream: false,
      }),
      // 25s timeout — Groq is usually <2s for this size.
      signal: AbortSignal.timeout(25_000),
    });
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    return NextResponse.json<RagError>(
      {
        error: 'Failed to reach the Groq API.',
        detail,
      },
      { status: 502 },
    );
  }

  if (!groqRes.ok) {
    let detail = '';
    try {
      const errBody = await groqRes.text();
      detail = errBody.slice(0, 500);
    } catch {
      /* ignore */
    }
    // Map common cases to friendlier status codes.
    const status = groqRes.status === 429 ? 429 : 502;
    return NextResponse.json<RagError>(
      {
        error:
          groqRes.status === 429
            ? 'Groq rate limit hit. Try again in a few seconds.'
            : `Groq API returned ${groqRes.status}.`,
        detail,
      },
      { status },
    );
  }

  type GroqChoice = { message?: { role?: string; content?: string } };
  type GroqResponse = {
    choices?: GroqChoice[];
    usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };

  let groqJson: GroqResponse;
  try {
    groqJson = (await groqRes.json()) as GroqResponse;
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    return NextResponse.json<RagError>(
      { error: 'Groq returned a non-JSON response.', detail },
      { status: 502 },
    );
  }

  const answer = groqJson.choices?.[0]?.message?.content?.trim() || '';

  if (!answer) {
    return NextResponse.json<RagError>(
      { error: 'Groq returned an empty answer. Try rephrasing your question.' },
      { status: 502 },
    );
  }

  const response: RagResponse = {
    answer,
    sources,
    intent,
    model: GROQ_MODEL,
    usage: groqJson.usage,
  };
  return NextResponse.json(response);
}

// ----------------------------------------------------------------------------
// History trimming
// ----------------------------------------------------------------------------

function trimHistory(history: ChatMessage[]): ChatMessage[] {
  // Only keep user/assistant turns, in order, with valid shapes.
  const cleaned = history
    .filter(
      (m): m is ChatMessage =>
        !!m &&
        (m.role === 'user' || m.role === 'assistant') &&
        typeof m.content === 'string' &&
        m.content.length > 0,
    )
    .slice(-MAX_HISTORY_MESSAGES);

  // Cap by total character count (rough proxy for tokens).
  let total = 0;
  const out: ChatMessage[] = [];
  for (let i = cleaned.length - 1; i >= 0; i--) {
    const m = cleaned[i];
    if (total + m.content.length > MAX_HISTORY_CHARS) break;
    out.unshift(m);
    total += m.content.length;
  }
  return out;
}
