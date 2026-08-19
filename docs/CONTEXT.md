# CONTEXT.md — SIH25071: AI-Based Rockfall Prediction and Alert System

Read this before touching code. Don't re-explain basics back to the user, don't hedge with generic ML advice, don't assume anything not stated here — ask if unclear.

## Problem
SIH25071, Ministry of Mines, Disaster Management theme. Build an AI/ML system that assesses rockfall risk in open-pit mines using environmental/geological data, predicts risk, and issues timely alerts for worker safety. Solo dev, hackathon deadline.

## Repo layout
Single repo: `~/Desktop/SIH2026/`
```
SIH2026/
├── frontend/   Next.js 16.3.1, App Router, TS, Turbopack, Tailwind
├── backend/    FastAPI 0.141.x, Python 3.12, venv
├── .gitignore
└── README.md
```
One git repo at root — no nested `.git` folders.

## Confirmed stack (verified live, do not substitute from training-data defaults)
- Frontend: Next.js 16.3.1, React 19.2.x, Node ≥20.9 (dev machine on v24), TypeScript 5.9.3 (**held back from TS7 — eslint-config-next not yet compatible, do not upgrade**), ESLint 9.x (**held back from v10 — same reason**), Tailwind 4.x
- Charts: **recharts** (current default for React/App Router dashboards)
- Map/heatmap: **maplibre-gl + react-map-gl** (MIT, no API key — chosen over Mapbox GL specifically to avoid a paid/token dependency this close to demo)
- Backend: FastAPI 0.141.x, uvicorn, Python 3.12
- Deployment target: Vercel (frontend) + Render (backend). UploadThing optional/unconfirmed.
- Alerts: Twilio SMS — unconfirmed, budget/keys not sorted yet

## Work streams / responsibilities (solo end-to-end ownership)
1. Geospatial/data — DEM (Copernicus GLO-30 via GEE), slope/curvature/aspect, Sentinel-1 SAR backscatter (GEE), rainfall API
2. Synthetic sensor data — physics-informed generator (displacement, vibration, pore pressure, strain) with labeled precursor events, calibrated against real datasets
3. ML baseline — RF/XGBoost, SHAP, **class imbalance handling is a required deliverable** (SMOTE/cost-sensitive/class weighting), report precision/recall/F1 on minority (rockfall) class, not accuracy
4. ML deep learning + edge — LSTM/GRU on time series, optional CNN-LSTM if imagery used, ONNX export for edge
5. Backend/API — FastAPI live simulated feed, WebSocket push, inference endpoint, alert-trigger logic, owns Render deploy
6. Frontend/dashboard — pit map + risk heatmap, live updates, trend charts, alert log, owns Vercel deploy + pitch deck

## Scientific grounding — treat as established fact, cite in pitch/docs
- **Inverse velocity method (Fukuzono, 1985)**: displacement rate accelerates before failure, inverse trends to zero at failure — this is the physical basis for "precursor" patterns, not arbitrary.
- **SSR (Slope Stability Radar)** is the real deployed gold standard (e.g. Kusmunda Mines, SECL India), sub-mm precision, ~$250k–500k/unit, line-of-sight only. **Pitch framing**: we're not inventing rockfall prediction — we're fusing cheaper, distributed sensor/satellite/weather data to extend coverage where full radar isn't affordable. Preserve this framing in all pitch material.
- **SAR backscatter, not InSAR**: our Sentinel-1 pull via GEE (COPERNICUS/S1_GRD) is amplitude backscatter, not phase-based interferometry. We do not claim mm-precision deformation — backscatter change is used as a proxy signal for surface disturbance (moisture, roughness change) preceding failure. State this proactively to judges; don't let it surface as a gap.
- **Real risk thresholds** (Indonesian open-pit coal SSR case study), adapt to our units: Safe 0–50mm/day, Warning 50–120mm/day, Evacuation >120mm/day displacement velocity. Use these, not arbitrary cutoffs.
- **Class imbalance is the central ML challenge** — rockfall events are rare. Near-certain judge question: "what if your model just predicts safe always?" Answer must be rehearsed and correct (imbalance-aware metrics).
- **Reference architecture** (IEEE paper, same SIH problem): hybrid CNN-LSTM-ensemble fusing drone imagery, micro-seismic, geotechnical sensors, environment; edge-AI deployable; ~30min mean alert lead time vs conventional ML. This is the bar to be aware of, not necessarily replicate fully.
- **Datasets for calibration/credibility, not primary training**: Landslide4Sense, NASA Global Landslide Catalog (Kaggle), Dorren et al. rockfall dataset (Zenodo), data.gov.in Mining + GSI/DGMS (India-specific credibility, Ministry of Mines problem statement).
- **Nice-to-have**: DBSCAN spatiotemporal clustering on displacement data to auto-identify risk zones instead of manual gridding (2025 Bayan Obo study) — only if bandwidth allows.
- **Model progression** (matches literature consensus, don't deviate without evidence): RF/XGBoost baseline → LSTM/GRU → hybrid/ensemble (CNN-LSTM).

## v2 Data Generation — Terrain-Modulated Risk Score (Phase 7 fix, 2026-08-20)

**Root cause fixed**: v1 `phase7_synthetic_sensors.py` assigned `risk_level` purely from hard displacement thresholds (Safe <50, Warning 50–120, Evacuation >120 mm/day). Terrain/SAR features (slope, curvature, VV/VH backscatter) were joined in as context but never causally affected the label. Result confirmed by v1 SHAP analysis: both models were functionally single-feature displacement-threshold detectors despite 10-feature input.

**Fix**: `risk_score = displacement_mm_day × susceptibility_multiplier(zone)`, where the multiplier is derived from the terrain/SAR susceptibility composite (slope×0.50 + curvature×0.30 + SAR×0.20), rescaled [0,1]→[0.70, 1.30]. The SSR thresholds (50/120 mm/day) are applied to `risk_score`, not raw displacement. Displacement ranges were also redesigned to overlap substantially across zone tiers so the same displacement value in different terrain zones yields different class labels — forcing genuine geospatial feature learning.

**v1 → v2 → v2b → v2c Evolution & SHAP Analysis:**

- **v1 (baseline)**: 0 crossover pairs (due to hard displacement clips). Terrain/SAR signal: XGBoost 0.00%, RF 12.27%.
- **v2 (validated final design)**: 75 crossover pairs out of 5,696 rows. Terrain/SAR signal: XGBoost 6.75%, RF 18.63%. This is the current production design.
- **v2b (isolation test — multiplier alone, original range)**: Tested whether the terrain multiplier by itself (range [0.70, 1.30]), without range-widening, could produce meaningful class-boundary crossings. Result: 0 crossover pairs, XGBoost 0.00%, RF 30.31%.
- **v2c (isolation test — multiplier alone, aggressive range [0.50, 1.60])**: Re-tested with a much wider, physically aggressive multiplier range, still without range-widening. Result: only 3 crossover pairs out of 5,696 rows (0.05%). XGBoost 0.00% (unchanged from v2b). RF 30.31% (identical to v2b to four decimal places).

**Key Conclusions:**
1. **RF spatial artifact**: RF's 30.31% is stable across v2b and v2c regardless of multiplier strength. This proves RF's terrain number is a zone-identity/spatial-autocorrelation proxy (slope correlates with zone tier), NOT a signal driven by the multiplier mechanism itself.
2. **Geometric capability vs dynamics**: The terrain multiplier alone is geometrically capable of crossing class boundaries, but generation dynamics keep displacement clustered away from clip edges except in rare peak-monsoon coincidences.
3. **Range-widening is structural**: Range-widening (as used in v2) is what creates a large enough overlap band for the multiplier to produce a learnable signal at this row count — it is structurally necessary, not incidental. The multiplier and range design work together.
4. **Loop closed**: v2b shows multiplier alone (normal range) fails; v2c shows multiplier alone (aggressive range) still fails. No further isolation testing needed.

*Pitch sentence verbatim for summary/pitch section:*
"We tested whether the terrain multiplier alone — even at a physically aggressive [0.50, 1.60] range — could produce meaningful class-boundary crossings under tight displacement clips. It produced only 3 crossover pairs out of 5,696 rows, too sparse for either model to learn from. This confirmed that overlapping displacement ranges are structurally necessary, not incidental — the terrain multiplier and the range design work together, and we can show exactly why."

*Note on RF Artifact (Appendix/Footnote):*
"RF's terrain contribution is stable regardless of multiplier strength because it's driven by spatial autocorrelation between slope and zone tier, not by the label-generation mechanism — confirmed via a controlled multiplier-range test."

History preserved, not rewritten: v1 numbers are the "before" baseline. v2 is the validated fix. The before/after comparison and isolation tests (v2b/v2c) are evidence of extreme methodological rigor. Cite this in the pitch if probed on label integrity.

**Physical justification** (pitch-ready): In real SSR practice, the same surface velocity at a steep concave bench triggers a higher alarm level than at a gentle slope — the instrument's context-aware threshold adjustment is exactly what `risk_score = displacement × susceptibility_multiplier` models. This is not an arbitrary scaling; it directly mirrors how operators interpret SSR data in the field (Wyllie & Mah, 2004, Rock Slope Engineering).

## Offline/edge deployment (optional, low priority — do not let this eat time from imbalance handling or threshold grounding)
- Architecture: sensors → edge device (e.g. Raspberry Pi) physically at the pit, running inference **locally** via **ONNX Runtime** (chosen over TFLite — faster on ARM CPU, one format covers XGBoost + LSTM + CNN-LSTM). Local alert (siren/GPIO/local SMS via GSM module) fires without internet. Cloud dashboard syncs opportunistically when connectivity returns.
- No mobile app needed — doesn't solve the offline problem (phone still needs a link to something local) and is unnecessary scope for this problem statement.
- Buildable artifact if time allows: export trained model to ONNX, standalone Python script using `onnxruntime`, zero network calls, demoed wifi-off next to the normal online dashboard. This is a day-7/8 nice-to-have, not a blocker — if core system isn't solid by day 6, skip the live demo and keep this as an architecture slide only.

## What "great" means here
- Concrete, implementable depth — real code, real thresholds, real architecture, tied to research above. No generic hackathon advice.
- Every system claim traceable to something real (cited technique, real threshold, real dataset).
- Be upfront that sensor data is synthetic (deliberate, defensible choice — no live mine access) while DEM/rainfall/SAR backscatter/calibration datasets are real. Don't blur this line.
- Push back on scope creep (extra services, unproven APIs, fragile infra) close to demo day — say so directly.
- No sycophancy, no filler.

## Open questions — do not assume, ask if relevant
- Exact mine location/region for DEM+rainfall+SAR backscatter pull (not chosen — real Indian coal/iron-ore pit preferred for authenticity)
- Twilio confirmed? API keys/budget sorted?
- Do I have access to real Pi/Jetson hardware, or stays "designed for" only?

## Operating instructions for the agent
- Real runnable code when asked for code, not pseudocode dressed up.
- Search the web for anything time-sensitive (library versions, API/dataset access, deployment quirks) — don't answer from possibly-stale memory. This project has already been through multiple verify-don't-assume passes; keep that bar.
- One direct clarifying question when genuinely ambiguous; infer everything else from this doc.
- Treat each follow-up (questions, errors, snippets) as continuation of this same project.
- Output should be copy-paste ready, not conceptual.