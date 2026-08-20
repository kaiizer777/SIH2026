# WORKFLOW.md — SIH25071 Rockfall Prediction: Day 0 → Demo

Companion to CONTEXT.md. This is the execution plan. Follow the order — the contract-first step on Day 0/1 is what prevents Day 6-7 becoming a bottleneck.

---

## Day 0 (before Day 1 — ~2 hrs) — [COMPLETED ✅]

1. **Repo scaffold** `[DONE ✅]`
   - `SIH2026/frontend` — Next.js 16.3.1, App Router, TS 5.9.3, Tailwind 4.x
   - `SIH2026/backend` — FastAPI 0.141.x, Python 3.12, venv
   - Single `.git` at root. No nested repos.

2. **Freeze the data contract** — this is the single most important artifact in the project. Everything builds against it, no improvising JSON shapes later across backend and frontend. `[DONE ✅]`
   - `backend/app/schemas.py` — Pydantic models for: sensor reading, risk prediction, alert event, WebSocket message envelope.
   - `frontend/lib/types.ts` — hand-mirrored TS types (or generated from the OpenAPI schema FastAPI already produces at `/openapi.json`).
   - Minimum fields to lock now:
     - `SensorReading`: `sensor_id`, `zone_id`, `timestamp`, `displacement_mm_day`, `vibration`, `pore_pressure`, `strain`, `rainfall_mm`
     - `RiskPrediction`: `zone_id`, `timestamp`, `risk_level` (`safe` / `warning` / `evacuation`), `risk_score` (0-1), `displacement_velocity_mm_day`, `model_version`
     - `AlertEvent`: `alert_id`, `zone_id`, `severity`, `message`, `triggered_at`, `acknowledged`
   - Thresholds baked in from CONTEXT.md, not arbitrary: Safe 0–50mm/day, Warning 50–120mm/day, Evacuation >120mm/day.

3. **Stub the mock inference endpoint immediately** (see Day 1 below — this is why it's listed first). Everything downstream depends on this existing before real models are ready. `[DONE ✅]`
   - `POST /predict` (weighted 60% safe / 25% warning / 15% evacuation) and `WebSocket /ws/feed` live stream with `ConnectionManager` are stood up.

4. **Register a Google Cloud project for Earth Engine access now, not Day 1.** *(Manual human action)* GEE requires `ee.Authenticate()` + `ee.Initialize(project='your-project')` against a registered Cloud project — there's no bare API-key mode. This is a one-time setup (register at the Earth Engine access page, enable the Earth Engine API on the project) but it involves account verification that can take a few minutes to hours, so do it before Day 1 starts, not when SAR backscatter pulling is already blocking.

---

## Day 1–2

**Geospatial/data**
- Pull Copernicus GLO-30 DEM for the chosen pit region directly via GEE (projects/sat-io/open-datasets/GLO-30) — same authenticated session as the SAR pull, no separate OpenTopography key needed.
- Derive slope, aspect, curvature (via `richdem`, `rasterio`, or GDAL).
- Pull Sentinel-1 SAR backscatter (VV/VH) via Google Earth Engine (GEE) Python API for the same region — backscatter change detection time series, used as a surface-disturbance proxy signal.
- Pull rainfall time series via **Open-Meteo** (historical + forecast API, no key required — verified good fit for a hackathon timeline).
- Output: a clean per-zone feature table (zone_id → slope, aspect, curvature, SAR backscatter change detection, rainfall) to join downstream feature pipelines against.
- **Open question — needs an answer before this can start for real**: exact mine location/region. Use a real Indian open-pit coal or iron-ore site if not yet chosen (Kusmunda-style framing helps the pitch).

**Synthetic sensor data**
- Physics-informed generator producing time series: displacement, vibration, pore pressure, strain.
- Base the precursor pattern on the **inverse velocity method (Fukuzono, 1985)** — displacement rate accelerates and its inverse trends toward zero approaching failure. This is your citable justification, not an arbitrary curve shape.
- Target class distribution: **Low 60% / Medium 25% / High 15%** (from the 2026 physics-informed rockfall paper) — use this instead of guessing an imbalance ratio.
- Calibrate against real datasets for sanity, not as primary training data: Landslide4Sense, NASA Global Landslide Catalog (Kaggle), Dorren et al. (Zenodo).
- Output format must match `SensorReading` schema exactly — verify against `backend/app/schemas.py` before writing final output.
- **[v2 fix, DONE ✅ 2026-08-20]** `risk_score = displacement × susceptibility_multiplier` label generation. Original v1 labels were pure displacement thresholds — terrain/SAR features were contextual only, not causal. v2 redesign: multiplier [0.70–1.30] from terrain composite forces geospatial features to genuinely determine class for overlapping displacement values. See `CONTEXT.MD § v2 Data Generation` for full rationale and v1/v2 SHAP before/after table.

**Backend — parallel, starts Day 1, not Day 6**
- Stand up FastAPI skeleton with the schemas from Day 0.
- Ship a **mock `/predict` endpoint** returning random-but-plausible `RiskPrediction` objects matching the schema (weighted 60/25/15 to match the real target distribution, so the dashboard's visual behavior isn't misleading during parallel dev).
- Ship a **mock WebSocket `/ws/feed`** that broadcasts a fake `SensorReading` + `RiskPrediction` every few seconds using a `ConnectionManager` broadcast pattern (accept → track connections → background task pushes → clean up on disconnect). This is the standard, well-tested FastAPI pattern for live dashboards at hackathon scale — no need for Redis pub/sub or multi-worker scaling, that's for 10K+ concurrent connections, not a demo.
- This mock is what the frontend builds against for the next 4 days. **Swapping the mock for the real model later should require zero frontend changes** if the schema was followed.

---

## Day 2–4

**ML baseline — [DONE ✅ 2026-08-20]**
- [x] **Phase 10**: Temporal split (not random/group) — cutoff 2026-06-03 (test), 2026-04-07 (val). Zero temporal leakage confirmed. Evacuation test set: 197 rows (17.3%).
- [x] **Phase 11**: Class weighting (`compute_sample_weight('balanced', y_train)`) — balanced effective weight ~0.53 (safe) / 1.29 (warning) / 2.84 (evacuation).
- [x] **Phase 12**: RF (n_estimators=300) and XGBoost (n_estimators=300, max_depth=6) trained on 3648 train rows with 10 features (4 sensor + 6 terrain/SAR). Both score 100% val accuracy (expected — synthetic data has clean patterns). Artifacts: `models/rf-v2-20260820.joblib`, `models/xgb-v2-20260820.joblib`.
- [x] **Phase 13**: SHAP analysis on val set, evacuation class. v2 results vs v1 baseline:
  - RF: terrain/SAR 18.63% (was 12.27% v1, +6.4pp). Top terrain feature: `slope` (rank 4 overall).
  - XGBoost: terrain/SAR 6.75% (was 0.00% v1, +6.75pp). `curvature` and `aspect` now non-zero contributors.
  - Displacement remains top feature in both (expected — it's the primary physical signal). Models are no longer *purely* displacement-threshold classifiers. SHAP plots: `reports/shap_randomforest_evacuation.png`, `reports/shap_xgboost_evacuation.png`.
- [x] Phase 13 also includes classification_report on **test set** — completed (Phase 14 Test Set Eval).
  - RF: Accuracy 97.71%. Evacuation F1: 0.99. Terrain/SAR SHAP: 17.03% (vs 18.63% val).
  - XGBoost: Accuracy 97.98%. Evacuation F1: 0.99. Terrain/SAR SHAP: 6.90% (vs 6.75% val).
  - Out-of-sample metrics perfectly align with validation. No material divergence.

**Frontend/dashboard — building against mock backend, starting Day 2**
- Pit map + risk heatmap using **maplibre-gl + react-map-gl** (no API key needed, avoids a paid dependency this close to demo).
- Charts (displacement/vibration/rainfall trends over time) using **recharts**.
- Live updates via the WebSocket contract from Day 1.
- Alert log view consuming `AlertEvent`.
- By end of Day 4 this should be a fully working dashboard against mock data — indistinguishable in the UI from the final version.

---

## Day 4–6

**Deep learning + edge**
- LSTM/GRU on the time-series sensor data; optional CNN-LSTM if imagery/SAR backscatter raster features are folded in.
- Benchmark against the RF/XGBoost baseline **using the same imbalance-aware metrics** — not a separately-defined eval. This comparison table is a core pitch asset.
- Export to ONNX (chosen over TFLite — one format covers XGBoost + GRU + CNN-LSTM, better ARM CPU perf) — needed only if edge deployment (Day 7-8) happens.

**Backend**
- Swap mock `/predict` for the real trained model (RF/XGBoost baseline first, upgrade to deep learning model if ready and better on the minority-class metrics).
- Wire the synthetic data generator into the live feed loop, replacing the random mock generator.
- Alert-trigger logic: when `risk_level` crosses into `warning` or `evacuation`, emit an `AlertEvent` over the same WebSocket channel — reuse the broadcast pattern from Day 1, don't build a second channel.
- Start Render deployment now, not Day 7 — deploying a working-but-simple version early surfaces environment issues (Python version mismatches, missing env vars) while there's still slack to fix them.

**Frontend**
- Point the dashboard at the real backend URL (local first, then Render once live).
- Fix any schema drift that surfaces now — this should be minimal if Day 0's contract was followed.
- Polish heatmap coloring to match the three risk bands visually and consistently with the pitch deck.

---

## Day 6–7

- Full integration test: real sensor generator → real model → FastAPI → WebSocket → dashboard, end to end, no mocks left in the loop.
- Finish Render deploy for backend; finish Vercel deploy for frontend.
- Cross-check: does a simulated "evacuation" event actually propagate from generator to a visible alert on the dashboard within a few seconds? Test this explicitly, don't assume it from unit-level testing.
- **Edge deployment piece fits here only if there's slack** — it's a side artifact, not a blocking dependency for anything else. If core system isn't fully solid by end of Day 6, skip live edge demo and keep it as an architecture slide only.
  - If attempted: standalone Python script using `onnxruntime`, zero network calls, demoed wifi-off next to the normal online dashboard.

---

## Day 7–8

- Polish, pitch deck, demo rehearsal.
- Pitch framing to lock in: **SSR (Slope Stability Radar)** is the real deployed gold standard (e.g., Kusmunda Mines, SECL) — sub-mm precision, $250k–500k/unit, line-of-sight only. Frame your system as extending coverage where full radar isn't affordable, fusing cheaper distributed sensor/satellite/weather data — not "inventing" rockfall prediction.
- Be explicit and upfront in the deck: sensor data is synthetic (deliberate, defensible — no live mine access), DEM/rainfall/SAR backscatter/calibration datasets are real. Don't blur this line; judges will ask.
- Rehearse the imbalance-metric answer out loud — it's the single most likely technical challenge question.
- Mention the prior SIH25071 GitHub solution's own "Future Scope" (real-time sensor feeds, cloud deployment) as validation — you built what last year's baseline explicitly called future work.

---

## Cross-cutting rules (apply every day)

- Any schema change must be manually re-checked against backend and frontend consumers before proceeding — nothing catches drift automatically now.
- Every risk threshold, dataset, and technique claim in the pitch must trace back to something real (cited paper, real dataset, real deployed system) — no invented numbers.
- Don't add scope (extra services, unproven APIs, new infra) after Day 6.