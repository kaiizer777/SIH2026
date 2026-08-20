# ── Frontend Dockerfile ───────────────────────────────────────────────────────
# Multi-stage build:
#   deps    → install node_modules
#   builder → next build (production bundle)
#   runner  → minimal image that just runs `next start`
#
# NEXT_PUBLIC_* vars are baked at build time (Next.js behaviour).
# Server-side vars (GROQ_API_KEY) are injected at runtime via docker-compose.
# ─────────────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install --prefer-offline

# ─── builder ─────────────────────────────────────────────────────────────────
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# These must be provided as --build-arg or in docker-compose build.args
ARG NEXT_PUBLIC_API_URL=http://localhost:8001
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8001/ws/feed

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL \
    # Skip ESLint & type-check during image build for CI speed;
    # run them separately in your CI pipeline.
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ─── runner ──────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 nextjs

# Only copy the minimum required to run `next start`
COPY --from=builder /app/public        ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static    ./.next/static

USER nextjs
EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
