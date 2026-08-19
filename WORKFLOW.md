# WORKFLOW.md — SIH25071 Rockfall Prediction: Day 0 → Demo

Companion to CONTEXT.md. This is the execution plan. Follow the order — the contract-first step on Day 0/1 is what prevents Day 6-7 becoming a bottleneck.

---

## Day 0 (before Day 1 — ~2 hrs, whole team, do this first)

1. **Repo scaffold**
   - `SIH2026/frontend` — Next.js 16.3.1, App Router, TS 5.9.3, Tailwind 4.x
   - `SIH2026/backend` — FastAPI 0.141.x, Python 3.12, venv
   - Single `.git` at root. No nested repos.

2. **Freeze the data contract** — this is the single most important artifact in the project. Everyone builds against it, nobody improvises their own JSON shape later.
   - `backend/app/schemas.py` — Pydantic models for: sensor reading, risk prediction, alert event, WebSocket message envelope.
   - `frontend/lib/types.ts` — hand-mirrored TS types (or generated from the OpenAPI schema FastAPI already produces at `/openapi.json`).
   - Minimum fields to lock now:
     - `SensorReading`: `sensor_id`, `zone_id`, `timestamp`, `displacement_mm_day`, `vibration`, `pore_pressure`, `strain`, `rainfall_mm`
     - `RiskPrediction`: `zone_id`, `timestamp`, `risk_level` (`safe` / `warning` / `evacuation`), `risk_score` (0-1), `displacement_velocity_mm_day`, `model_version`
     - `AlertEvent`: `alert_id`, `zone_id`, `severity`, `message`, `triggered_at`, `acknowledged`
   - Thresholds baked in from CONTEXT.md, not arbitrary: Safe 0–50mm/day, Warning 50–120mm/day, Evacuation >120mm/day.

3. **Person 5 stubs the mock inference endpoint immediately** (see Day 1 below — this is why it's listed first). Everything downstream depends on this existing before real models are ready.

---

## Day 1–2

**Person 1 (Geospatial/data)**
- Pull DEM (SRTM or Copernicus GLO-30) for the chosen pit region.
- Derive slope, aspect, curvature (via `richdem`, `rasterio`, or GDAL).
- Pull Sentinel-1 InSAR via Google Earth Engine (GEE) Python API for the same region — deformation time series.
- Pull rainfall time series (Open-Meteo or IMD API — Open-Meteo needs no key, good for a hackathon).
- Output: a clean per-zone feature table (zone_id → slope, aspect, curvature, InSAR deformation, rainfall) other people can join against.
- **Open question — needs an answer before this can start for real**: exact mine location/region. Use a real Indian open-pit coal or iron-ore site if not yet chosen (Kusmunda-style framing helps the pitch).

**Person 2 (Synthetic sensor data)**
- Physics-informed generator producing time series: displacement, vibration, pore pressure, strain.
- Base the precursor pattern on the **inverse velocity method (Fukuzono, 1985)** — displacement rate accelerates and its inverse trends toward zero approaching failure. This is your citable justification, not an arbitrary curve shape.
- Target class distribution: **Low 60% / Medium 25% / High 15%** (from the 2026 physics-informed rockfall paper) — use this instead of guessing an imbalance ratio.
- Calibrate against real datasets for sanity, not as primary training data: Landslide4Sense, NASA Global Landslide Catalog (Kaggle), Dorren et al. (Zenodo).
- Output format must match `SensorReading` schema exactly — coordinate with Person 5 before writing final output.

**Person 5 (Backend) — parallel, starts Day 1, not Day 6**
- Stand up FastAPI skeleton with the schemas from Day 0.
- Ship a **mock `/predict` endpoint** returning random-but-plausible `RiskPrediction` objects matching the schema (weighted 60/25/15 to match the real target distribution, so the dashboard's visual behavior isn't misleading during parallel dev).
- Ship a **mock WebSocket `/ws/feed`** that broadcasts a fake `SensorReading` + `RiskPrediction` every few seconds using a `ConnectionManager` broadcast pattern (accept → track connections → background task pushes → clean up on disconnect). This is the standard, well-tested FastAPI pattern for live dashboards at hackathon scale — no need for Redis pub/sub or multi-worker scaling, that's for 10K+ concurrent connections, not a demo.
- This mock is what Person 6 builds against for the next 4 days. **Swapping the mock for the real model later should require zero frontend changes** if the schema was followed.

---

## Day 2–4

**Person 3 (ML baseline)**
- Train RF and XGBoost on Person 2's synthetic data (once schema-compliant).
- **Class imbalance handling is a required deliverable, not optional**: SMOTE, class weighting, or cost-sensitive loss — pick one, implement it, be ready to explain the choice.
- Report **precision/recall/F1 on the minority (rockfall/high-risk) class**. Do not report plain accuracy as your headline metric — a model that always predicts "safe" scores ~85%+ accuracy on this distribution and is useless. Rehearse this answer; it's a near-certain judge question.
- Use SHAP for feature importance — ties back to Person 1's geospatial features for interpretability in the pitch.
- Export model artifact (pickle/joblib) with a version string that matches `model_version` in the schema.

**Person 6 (Frontend/dashboard) — building against Person 5's mock, starting Day 2**
- Pit map + risk heatmap using **maplibre-gl + react-map-gl** (no API key needed, avoids a paid dependency this close to demo).
- Charts (displacement/vibration/rainfall trends over time) using **recharts**.
- Live updates via the WebSocket contract from Day 1.
- Alert log view consuming `AlertEvent`.
- By end of Day 4 this should be a fully working dashboard against mock data — indistinguishable in the UI from the final version.

---

## Day 4–6

**Person 4 (Deep learning + edge)**
- LSTM/GRU on the time-series sensor data; optional CNN-LSTM if imagery/InSAR raster features are folded in.
- Benchmark against Person 3's RF/XGBoost baseline **using the same imbalance-aware metrics** — not a separately-defined eval. This comparison table is a core pitch asset.
- Export to ONNX (chosen over TFLite — one format covers XGBoost + LSTM + CNN-LSTM, better ARM CPU perf) — needed only if edge deployment (Day 7-8) happens.

**Person 5 (Backend)**
- Swap mock `/predict` for the real trained model (Person 3's baseline first, upgrade to Person 4's model if ready and better on the minority-class metrics).
- Wire the synthetic data generator (Person 2) into the live feed loop, replacing the random mock generator.
- Alert-trigger logic: when `risk_level` crosses into `warning` or `evacuation`, emit an `AlertEvent` over the same WebSocket channel — reuse the broadcast pattern from Day 1, don't build a second channel.
- Start Render deployment now, not Day 7 — deploying a working-but-simple version early surfaces environment issues (Python version mismatches, missing env vars) while there's still slack to fix them.

**Person 6 (Frontend)**
- Point the dashboard at the real backend URL (local first, then Render once live).
- Fix any schema drift that surfaces now — this should be minimal if Day 0's contract was followed.
- Polish heatmap coloring to match the three risk bands visually and consistently with the pitch deck.

---

## Day 6–7

- Full integration test: real sensor generator → real model → FastAPI → WebSocket → dashboard, end to end, no mocks left in the loop.
- Person 5 finishes Render deploy; Person 6 finishes Vercel deploy.
- Cross-check: does a simulated "evacuation" event actually propagate from generator to a visible alert on the dashboard within a few seconds? Test this explicitly, don't assume it from unit-level testing.
- **Edge deployment piece fits here only if there's slack** — it's a side artifact, not a blocking dependency for anything else. If core system isn't fully solid by end of Day 6, skip live edge demo and keep it as an architecture slide only.
  - If attempted: standalone Python script using `onnxruntime`, zero network calls, demoed wifi-off next to the normal online dashboard.

---

## Day 7–8

- Polish, pitch deck, demo rehearsal.
- Pitch framing to lock in: **SSR (Slope Stability Radar)** is the real deployed gold standard (e.g., Kusmunda Mines, SECL) — sub-mm precision, $250k–500k/unit, line-of-sight only. Frame your system as extending coverage where full radar isn't affordable, fusing cheaper distributed sensor/satellite/weather data — not "inventing" rockfall prediction.
- Be explicit and upfront in the deck: sensor data is synthetic (deliberate, defensible — no live mine access), DEM/rainfall/InSAR/calibration datasets are real. Don't blur this line; judges will ask.
- Rehearse the imbalance-metric answer out loud as a team — it's the single most likely technical challenge question.
- Mention the prior SIH25071 GitHub solution's own "Future Scope" (real-time sensor feeds, cloud deployment) as validation — you built what last year's baseline explicitly called future work.

---

## Cross-cutting rules (apply every day)

- Nobody changes the schema from Day 0 without notifying Person 5 and Person 6 first — they're the two people whose work breaks silently if the contract drifts.
- Every risk threshold, dataset, and technique claim in the pitch must trace back to something real (cited paper, real dataset, real deployed system) — no invented numbers.
- Don't add scope (extra services, unproven APIs, new infra) after Day 6.