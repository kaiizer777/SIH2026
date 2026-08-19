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