# SIH2026 — Project Context & Complete Reference

> **Single source of truth** for every contributor, reviewer, judge, and future maintainer of the SIH25071 rockfall prediction system.  
> Last updated: Phase 29 (Day 7 end-of-review checklist).

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement & Motivation](#2-problem-statement--motivation)
3. [Physical & Scientific Grounding](#3-physical--scientific-grounding)
4. [Repository Layout](#4-repository-layout)
5. [Confirmed Tech Stack](#5-confirmed-tech-stack)
6. [Data Pipeline (Phases 1–9)](#6-data-pipeline-phases-19)
7. [ML Pipeline (Phases 10–16)](#7-ml-pipeline-phases-1016)
8. [Deep Learning (Phases 17–19)](#8-deep-learning-phases-1719)
9. [Backend Integration (Phases 20–24)](#9-backend-integration-phases-2024)
10. [Integration & Deploy Hardening (Phases 25–29)](#10-integration--deploy-hardening-phases-2529)
11. [Model Comparison & Evaluation](#11-model-comparison--evaluation)
12. [Data Generation Evolution (v1 → v2c)](#12-data-generation-evolution-v1--v2c)
13. [Frontend Design & Architecture](#13-frontend-design--architecture)
14. [API Reference](#14-api-reference)
15. [Data Schemas](#15-data-schemas)
16. [Deployment Architecture](#16-deployment-architecture)
17. [Edge Deployment (Optional)](#17-edge-deployment-optional)
18. [Test Suite](#18-test-suite)
19. [Open Questions & Unresolved Items](#19-open-questions--unresolved-items)
20. [Operating Instructions & Conventions](#20-operating-instructions--conventions)
21. [Pitch Framing & Defence Notes](#21-pitch-framing--defence-notes)
22. [Glossary](#22-glossary)

---

## 1. Project Overview

| Field | Value |
|---|---|
| **Problem Statement** | SIH25071 — AI-powered rockfall prediction and early-warning system for open-pit mines |
| **Theme** | Ministry of Mines — Disaster Management |
| **Goal** | Assess rockfall risk using environmental + geological data, predict risk levels, issue timely alerts to protect mine workers |
| **Development Model** | Solo developer, hackathon deadline (Smart India Hackathon 2026) |
| **Live Backend** | `https://sih2026-xk4z.onrender.com` |
| **Live Frontend** | `https://sih-2026-drab.vercel.app` |

The system ingests multi-source geospatial and sensor data (DEM terrain derivatives, Sentinel-1 SAR backscatter, historical rainfall, and synthetic physics-informed sensor streams), trains ML/DL models to classify zone-level rockfall risk into three tiers — **Safe**, **Warning**, **Evacuation** — and surfaces predictions + real-time alerts through a WebSocket-powered dashboard.

---

## 2. Problem Statement & Motivation

Open-pit mining is inherently hazardous. Slope failures and rockfalls kill hundreds of workers globally each year. The current gold standard for slope monitoring — **Slope Stability Radar (SSR)** — provides sub-millimetre displacement precision but costs $250k–$500k per unit and only covers line-of-sight angles. Most mines in developing nations cannot afford full SSR coverage across every bench and ramp.

**Our thesis:** fuse cheaper, distributed data sources — satellite SAR, terrain models, weather APIs, and IoT-style sensors — into an ML pipeline that extends predictive coverage to zones where full radar deployment is uneconomical. The system does not replace SSR; it **extends the safety perimeter**.

### Who Benefits

- **Mine workers** — receive early warnings before slope instability becomes catastrophic.
- **Mine operators** — gain coverage across the entire pit at a fraction of SSR cost.
- **Regulatory bodies** — get auditable risk logs and alert histories.

### What Success Looks Like

- High **Evacuation-class recall** — never miss a real evacuation event.
- Real-time alert delivery via WebSocket with sub-second latency.
- Honest, defensible model evaluation (no inflated accuracy claims).

---

## 3. Physical & Scientific Grounding

### 3.1 Inverse Velocity Method (Fukuzono, 1985)

The foundational physics model for slope failure prediction. As a slope approaches failure:

1. Displacement rate (velocity) **accelerates**.
2. The **inverse of velocity** (1/v) trends linearly toward **zero**.
3. The intercept with the time axis predicts the **failure time**.

Our synthetic data generator (`backend/app/physics_generator.py`) uses this model to produce realistic displacement acceleration patterns per zone, parameterised by zone susceptibility.

### 3.2 Slope Stability Radar (SSR)

- **What it is:** Ground-based real aperture radar that scans pit walls and measures surface displacement with sub-mm precision.
- **Where it's deployed:** Kusmunda Mine (SECL, Chhattisgarh) — our reference site — and many others globally.
- **Limitations:** Line-of-sight only (one wall at a time), $250k–$500k per unit, requires stable mounting infrastructure.
- **Our position:** SSR is the gold standard. We complement it, not compete with it.

### 3.3 SAR Backscatter (Sentinel-1 GRD)

- **Source:** Sentinel-1 C-band SAR, Copernicus programme, freely available via Google Earth Engine.
- **Product:** Ground Range Detected (GRD) amplitude backscatter — **not** InSAR (interferometric phase). This is an important distinction: we use backscatter intensity changes as a proxy for surface disturbance (cracks, loose material, moisture), not millimetre-scale displacement.
- **Polarisations:** VV and VH.
- **Track:** DESCENDING, Track 19 (relative orbit).
- **Resolution:** ~10m ground resolution after GEE processing.
- **Per-zone aggregation:** Backscatter values are averaged over each of the 16 zone polygons for each acquisition date, producing 480 rows (16 zones × 30 dates).

### 3.4 Real Risk Thresholds

From an Indonesian open-pit coal mine SSR case study (peer-reviewed):

| Risk Level | Displacement Threshold |
|---|---|
| **Safe** | 0–50 mm/day |
| **Warning** | 50–120 mm/day |
| **Evacuation** | >120 mm/day |

These thresholds are physically grounded and used in our synthetic data labelling.

### 3.5 Reference Architecture (IEEE Paper)

A hybrid CNN-LSTM ensemble architecture reported in IEEE literature achieves:

- Multi-sensor fusion (radar, weather, geological).
- ~30-minute mean alert lead time before failure.
- Our architecture is simpler (GRU + tree ensembles) but targets the same operational objective.

---

## 4. Repository Layout

```
SIH2026/
├── .github/
│   └── workflows/
│       └── keep-render-alive.yml          # Cron heartbeat (14-min interval) to prevent Render cold start
├── AGENTS.md                               # Operational directives for AI agents
├── README.md                               # Project README
├── render.yaml                             # Render deployment config
├── runtime.txt                             # Python runtime pin (Render)
├── work.md                                 # Scratch work notes
├── frontend.md                             # 450-line frontend design guide / style bible
│
├── docs/
│   ├── CONTEXT.md                          # ← THIS FILE — single source of truth
│   ├── WORKFLOW.md                         # Development workflow documentation
│   ├── session-done-01.md                  # Day 1–2: geospatial / data phases 1–9
│   ├── session-done-02.md                  # Day 2–4: ML baseline phases 10–16
│   ├── session-done-03.md                  # Day 4–6: deep learning + real backend phases 17–24
│   ├── pitch-01.txt … pitch-07.txt         # Pitch narrative drafts
│
├── backend/
│   ├── main.py                             # FastAPI app entrypoint (lifespan, CORS, router mount)
│   ├── schemas.py                          # Re-export convenience module
│   ├── requirements.txt                    # 47 pinned Python dependencies
│   ├── app/
│   │   ├── schemas.py                      # Pydantic models: SensorReading, RiskPrediction, AlertEvent
│   │   ├── physics_generator.py            # Fukuzono-based live sensor data generator
│   │   └── __init__.py
│   ├── routers/
│   │   └── rockfall.py                     # POST /predict, WS /ws/feed, alert logic, broadcast
│   ├── models/
│   │   └── __init__.py
│   ├── scripts/
│   │   ├── verify_gee.py                   # GEE authentication verification
│   │   └── ws_watch.py                     # WebSocket monitoring script
│   └── venv/                               # Python virtual environment (gitignored)
│
├── frontend/
│   ├── package.json                        # Next.js 16.3.1, React 19, maplibre-gl, recharts
│   ├── app/
│   │   ├── layout.tsx                      # Root layout (Geist fonts, metadata)
│   │   ├── page.tsx                        # Home / landing page
│   │   ├── globals.css                     # Tailwind 4.x + custom CSS tokens
│   │   ├── dashboard/
│   │   │   └── page.tsx                    # MapLibre 3D pit heatmap + summary metrics
│   │   ├── alerts/
│   │   │   └── page.tsx                    # Real-time alert dispatch log (WebSocket-fed)
│   │   ├── trends/
│   │   │   └── page.tsx                    # Recharts telemetry trend charts
│   │   ├── pitch/
│   │   │   └── (996-line pitch companion UI with AriaTab RAG chat)
│   │   └── api/
│   │       └── rag/                        # API route backing the RAG chat widget
│   ├── components/
│   │   ├── topbar/TopBar.tsx               # Global navigation bar
│   │   ├── map/PitHeatmap.tsx              # MapLibre GL 3D heatmap component
│   │   ├── charts/TrendChart.tsx           # Recharts wrapper component
│   │   └── ui/                             # Shared UI primitives
│   ├── lib/
│   │   ├── types.ts                        # TypeScript interfaces mirroring backend schemas
│   │   ├── api.ts                          # HTTP client helpers (fetch wrappers)
│   │   └── websocket.ts                    # WebSocket connection manager with reconnect
│   └── public/
│       └── style.json                      # MapLibre style definition
│
├── models/
│   ├── rf-v1-20260820.joblib               # RandomForest v1
│   ├── rf-v2-20260820.joblib               # RandomForest v2 (production)
│   ├── rf-v2b-20260820.joblib              # RF v2b isolation test
│   ├── rf-v2c-20260820.joblib              # RF v2c isolation test
│   ├── xgb-v1-20260820.joblib              # XGBoost v1
│   ├── xgb-v2-20260820.joblib              # XGBoost v2 (production)
│   ├── xgb-v2b-20260820.joblib             # XGBoost v2b isolation test
│   ├── xgb-v2c-20260820.joblib             # XGBoost v2c isolation test
│   ├── gru-v1-20260821.pt                  # PyTorch GRU model weights
│   ├── gru-v1-20260821_config.json         # GRU architecture config
│   ├── feature_order.json                  # Feature column order for v1/v2
│   ├── feature_order_v2b.json              # Feature order for v2b
│   ├── feature_order_v2c.json              # Feature order for v2c
│   ├── label_encoding.json                 # Label encoder mapping v1/v2
│   ├── label_encoding_v2b.json             # Label mapping v2b
│   └── label_encoding_v2c.json             # Label mapping v2c
│
├── data/
│   ├── aoi.json                            # Kusmunda Mine bounding box, Chhattisgarh
│   ├── zone_grid.json                      # 4×4 = 16 zone grid with GeoJSON polygons
│   ├── dem.tif                             # Copernicus GLO-30 DEM
│   ├── slope.tif                           # Slope derivative (richdem)
│   ├── aspect.tif                          # Aspect derivative (richdem)
│   ├── curvature.tif                       # Curvature derivative (richdem)
│   ├── sar_backscatter.csv                 # Sentinel-1 VV/VH per zone per date
│   ├── rainfall.csv                        # 356 daily records from Open-Meteo ERA5
│   ├── zone_features.csv                   # 480 rows: 16 zones × 30 SAR dates
│   ├── synthetic_sensors.csv               # 5,696 rows: 16 zones × 356 days (v2)
│   ├── synthetic_sensors_v2b.csv           # v2b isolation test data
│   ├── synthetic_sensors_v2c.csv           # v2c isolation test data
│   ├── train.csv / val.csv / test.csv      # Temporal split (v2)
│   ├── train_v2b.csv / val_v2b.csv / test_v2b.csv
│   ├── train_v2c.csv / val_v2c.csv / test_v2c.csv
│   ├── train_sample_weights.npy            # Class-balanced sample weights
│   ├── train_sample_weights_v2b.npy
│   ├── train_sample_weights_v2c.npy
│   ├── split_metadata.json                 # Temporal split cutoffs & row counts
│   ├── weights_metadata.json               # Weight computation metadata
│   └── sequences/
│       ├── train_sequences.npz             # GRU training sequences (14-day windows)
│       ├── val_sequences.npz               # GRU validation sequences
│       ├── test_sequences.npz              # GRU test sequences
│       └── manifest.json                   # Sequence counts, window size, feature list
│
├── scripts/
│   ├── phase3_terrain.py                   # DEM pull + terrain derivatives
│   ├── phase4_sar.py                       # SAR backscatter extraction
│   ├── phase5_rainfall.py                  # Rainfall data pull
│   ├── phase6_zone_features.py             # Zone feature table assembly
│   ├── phase7_synthetic.py                 # Synthetic sensor generation (v1/v2/v2b/v2c)
│   ├── phase10_split.py                    # Temporal train/val/test split
│   ├── phase11_weights.py                  # Class weight computation
│   ├── phase12_train.py                    # RF + XGBoost training
│   ├── phase13_shap.py                     # SHAP analysis
│   ├── phase14_eval.py                     # Test-set evaluation
│   ├── phase15_export.py                   # Model artifact export
│   ├── phase17_sequences.py                # GRU sequence framing
│   ├── phase18_gru_train.py                # GRU training loop
│   ├── phase19_gru_eval.py                 # GRU evaluation
│   ├── phase25_audit.py                    # Zero-mock audit
│   ├── phase27_ws_probe.py                 # WebSocket probe / hardening
│   └── scratch_shap.py                     # Ad-hoc SHAP experiments
│
├── tests/
│   ├── test_alert_dedup.py                 # Alert de-duplication logic
│   ├── test_physics_sanity.py              # Physics generator sanity checks
│   ├── test_predict_endpoint.py            # POST /predict endpoint
│   ├── test_ws_disconnect.py               # WebSocket disconnect handling
│   ├── test_ws_feed.py                     # WebSocket feed integration
│   └── test_ws_phase21.py                  # Phase 21 integration test
│
├── reports/                                # Confusion matrices, SHAP plots
└── test-results/                           # Test run outputs
```

---

## 5. Confirmed Tech Stack

### Frontend

| Technology | Version | Notes |
|---|---|---|
| **Next.js** | 16.3.1 | App Router, React Server Components |
| **React** | 19.2.x | Latest stable |
| **Node.js** | ≥20.9 | Required by Next.js 16 |
| **TypeScript** | 5.9.3 | Held back from TS7 (breaking changes) |
| **ESLint** | 9.x | Held back from v10 |
| **Tailwind CSS** | 4.x | CSS-first config, `@theme` inline |
| **recharts** | latest | Telemetry trend charts |
| **maplibre-gl** | latest | MIT-licensed, no API key required |
| **react-map-gl** | latest | React wrapper for MapLibre |

### Backend

| Technology | Version | Notes |
|---|---|---|
| **FastAPI** | 0.141.x | Async Python web framework |
| **uvicorn** | latest | ASGI server |
| **Python** | 3.12 | Pinned in runtime.txt |
| **Pydantic** | v2 | Schema validation (bundled with FastAPI) |

### ML / Data Science

| Technology | Use Case |
|---|---|
| **Scikit-learn** | RandomForest classifier, sample weights |
| **XGBoost** | Gradient-boosted tree classifier |
| **PyTorch** | GRU sequence model |
| **ONNX Runtime** | Edge deployment (planned) |
| **SHAP** | Model interpretability / feature importance |
| **NumPy** | Array operations, sample weight files |
| **Pandas** | Data wrangling |

### Geospatial

| Technology | Use Case |
|---|---|
| **Google Earth Engine (GEE)** | DEM pull, SAR backscatter extraction |
| **earthengine-api** | Python client for GEE |
| **rasterio** | GeoTIFF I/O |
| **richdem** | Terrain derivative computation (slope, aspect, curvature) |
| **Open-Meteo API** | Historical rainfall data (ERA5 archive) |

### Deployment

| Platform | Service | Notes |
|---|---|---|
| **Vercel** | Frontend | Auto-deploy on push, Next.js optimised |
| **Render** | Backend | Free tier, Python 3.12, sleeps after 15 min idle |
| **GitHub Actions** | Heartbeat | Cron every 14 min to prevent cold start |

---

## 6. Data Pipeline (Phases 1–9)

All phases complete. This section documents the provenance and characteristics of every dataset in `data/`.

### Phase 1 — Mine Site Lockdown

**Target site:** Kusmunda Mine, South Eastern Coalfields Limited (SECL), Chhattisgarh, India.

- Bounding box defined in `data/aoi.json`.
- Selected for: operational open-pit mine, existing SSR deployment (real-world validation reference), freely available satellite coverage.

### Phase 2 — GEE + Cloud Auth

- Google Earth Engine Python API authenticated via service account.
- Dependencies: `earthengine-api`, `richdem`, `rasterio`.
- Verification script: `backend/scripts/verify_gee.py`.

### Phase 3 — DEM Pull + Terrain Derivatives

- **Source:** Copernicus GLO-30 digital elevation model via GEE.
- **Output files:**
  - `data/dem.tif` — raw elevation.
  - `data/slope.tif` — slope angle (degrees), computed via richdem.
  - `data/aspect.tif` — slope aspect (degrees from north).
  - `data/curvature.tif` — profile curvature (concavity/convexity).
- **Processing:** GEE export to Google Cloud Storage → local download → richdem terrain analysis.

### Phase 4 — SAR Backscatter Extraction

- **Source:** Sentinel-1 GRD (COPERNICUS/S1_GRD), C-band SAR.
- **Mode:** DESCENDING, Track 19 (relative orbit).
- **Polarisations:** VV and VH.
- **Acquisitions:** 30 dates.
- **Output:** `data/sar_backscatter.csv` — VV and VH mean backscatter per zone per date.
- **Important distinction:** This is **amplitude backscatter** (surface reflectivity), not InSAR (interferometric phase). Backscatter changes correlate with surface disturbance, moisture, and roughness — useful as a contextual feature but not a displacement measurement.

### Phase 5 — Rainfall Data

- **Source:** Open-Meteo Historical Archive API (ERA5 reanalysis).
- **Period:** 356 daily records covering the synthetic sensor date range.
- **Output:** `data/rainfall.csv` — daily precipitation in mm.

### Phase 6 — Zone Feature Table

- **Zone grid:** 4×4 = 16 zones defined in `data/zone_grid.json` (GeoJSON polygons over the mine footprint).
- **Output:** `data/zone_features.csv` — 480 rows (16 zones × 30 SAR dates).
- **Columns:** zone_id, date, mean_VV, mean_VH, plus terrain derivatives aggregated per zone.

### Phase 7 — Synthetic Sensor Data

The most nuanced dataset. See [Section 12](#12-data-generation-evolution-v1--v2c) for the full evolution story.

- **Generator:** `backend/app/physics_generator.py` — implements Fukuzono (1985) inverse velocity model.
- **Parameters per zone:** susceptibility (from terrain/SAR), noise floor, acceleration profile.
- **Output (v2 — production):** `data/synthetic_sensors.csv` — 5,696 rows (16 zones × 356 days).
- **Columns:** sensor_id, zone_id, timestamp, displacement_mm_day, vibration, pore_pressure, strain, rainfall_mm, risk_level.
- **Labelling logic (v2):**
  1. Compute `risk_score = displacement × susceptibility_multiplier`.
  2. Apply thresholds on `risk_score` (not raw displacement).
  3. This produces physically meaningful class boundaries that interact with terrain context.

**v1 bug:** Labels were purely displacement-based; terrain and SAR features were contextual only and never influenced the label. This led to 0 crossover pairs and near-zero tree-model SHAP importance for contextual features.

**v2 fix:** The `risk_score` composite ensures that the same raw displacement produces different risk labels depending on zone susceptibility (steep, unstable terrain escalates risk).

### Phase 8 — Backend Mock Stability Check

- Verified that the FastAPI app starts cleanly with mock data paths.
- Confirmed schema validation round-trip.

### Phase 9 — End-of-Day-2 Review

- All data assets inventoried.
- Pipeline reproducibility confirmed.
- Session notes: `docs/session-done-01.md`.

---

## 7. ML Pipeline (Phases 10–16)

All phases complete.

### Phase 10 — Temporal Split

**Zero temporal leakage.** Data is split by date, not randomly:

| Split | Cutoff Date | Rows |
|---|---|---|
| **Train** | Before 2026-04-07 | ~3,800 |
| **Validation** | 2026-04-07 to 2026-06-03 | ~900 |
| **Test** | After 2026-06-03 | ~1,000 |

Metadata stored in `data/split_metadata.json`.

### Phase 11 — Class Weighting

- **Method:** `sklearn.utils.class_weight.compute_sample_weight('balanced')`.
- **Why not SMOTE:** Synthetic Minority Oversampling Technique generates synthetic samples by interpolating between existing minority-class neighbours. In our data, features are **physically correlated** across time (displacement is autocorrelated, rainfall has seasonality, SAR backscatter changes slowly). SMOTE would create physically impossible feature combinations — a zone cannot have high displacement, low rainfall, and high SAR backscatter simultaneously in a way that's plausible. Class weighting preserves the physical structure of every real sample.
- **Output:** `data/train_sample_weights.npy` (and v2b/v2c variants).
- **Metadata:** `data/weights_metadata.json`.

### Phase 12 — Model Training

**RandomForest (v2 — production):**
- `n_estimators=300`
- Scikit-learn implementation
- Class-weighted via sample_weight parameter

**XGBoost (v2 — production):**
- `n_estimators=300`
- `max_depth=6`
- Class-weighted via sample_weight parameter

Both trained on v2 data with temporal split and sample weights.

### Phase 13 — SHAP Analysis

SHAP (SHapley Additive exPlanations) values computed on the validation set.

**Key result (v2):**

| Model | Terrain + SAR SHAP Contribution |
|---|---|
| RandomForest | 18.63% |
| XGBoost | 6.75% |

This confirms that contextual features (terrain derivatives + SAR backscatter) contribute meaningfully to predictions — a direct consequence of the v2 labelling fix where `risk_score` incorporates zone susceptibility.

**v1 comparison:** RF terrain/SAR SHAP was 12.27%, XGBoost was near-zero. The v2 fix improved feature utilisation.

### Phase 14 — Test Evaluation

| Metric (Evacuation Class) | RandomForest (v2) | XGBoost (v2) |
|---|---|---|
| **Accuracy** | 97.71% | 97.98% |
| **Precision** | 0.9949 | 0.9704 |
| **Recall** | 0.9848 | 1.0000 |
| **F1-Score** | 0.9898 | 0.9850 |
| **Missed Evacuations** | 3/197 | 0/197 |

XGBoost achieves perfect recall on Evacuation (zero missed events). RF trades 3 missed evacuations for higher precision.

### Phase 15 — Model Artifact Export

All models serialized:
- RF/XGBoost: `.joblib` format (scikit-learn/XGBoost native).
- Feature order: `feature_order.json` (column order must match at inference time).
- Label encoding: `label_encoding.json` (maps numeric class → string label).

### Phase 16 — Review Checklist

All items cleared. Session notes: `docs/session-done-02.md`.

---

## 8. Deep Learning (Phases 17–19)

All phases complete.

### Phase 17 — GRU Sequence Framing

- **Window size:** 14 days (each input is a 14-timestep × 10-feature tensor).
- **Stride:** 1 day (sliding window).
- **Sequence counts:**
  - Train: 3,440 sequences
  - Validation: 912 sequences
  - Test: 1,136 sequences
- **Storage:** `data/sequences/*.npz` with manifest in `data/sequences/manifest.json`.
- **Features (10):** displacement_mm_day, vibration, pore_pressure, strain, rainfall_mm, slope, aspect, curvature, mean_VV, mean_VH.

### Phase 18 — GRU Training

- **Architecture:** Single-layer GRU.
  - `input_size=10` (features per timestep)
  - `hidden_size=64`
  - `num_classes=3`
- **Framework:** PyTorch.
- **Loss:** Class-weighted CrossEntropyLoss (same weighting rationale as tree models).
- **Optimiser:** Adam.
- **Early stopping:** Patience=8, best validation loss = 0.03216 at epoch 19.
- **Artifacts:** `models/gru-v1-20260821.pt` (weights), `models/gru-v1-20260821_config.json` (architecture).

### Phase 19 — GRU Evaluation

| Metric | Value |
|---|---|
| **Precision (Evacuation)** | 1.0000 |
| **Recall (Evacuation)** | 0.7208 |
| **F1-Score (Evacuation)** | 0.8378 |
| **Missed Evacuations** | 55/197 |

**Interpretation:** The GRU has perfect precision (every evacuation it predicts is correct) but lower recall (it misses 55 real evacuation events). All 55 misses fall in the **Warning** class — the GRU is conservative, predicting "Warning" when the true label is "Evacuation." It never predicts "Safe" for a real evacuation event.

**Why GRU is still included:** Architectural completeness. The GRU demonstrates that sequence modelling captures temporal acceleration patterns that tree models see only as flat feature vectors. In a production ensemble, GRU predictions could serve as a high-precision second opinion — if the GRU says "Evacuation," it's almost certainly correct.

---

## 9. Backend Integration (Phases 20–24)

All phases complete.

### Phase 20 — Real Model in /predict

- RF v2 model loaded during FastAPI lifespan (`main.py`).
- Feature order enforced via `feature_order.json`.
- Label mapping via `label_encoding.json`.
- Endpoint: `POST /predict` accepts `SensorReading`, returns `RiskPrediction`.

### Phase 21 — Real Generator in /ws/feed

- `backend/app/physics_generator.py` produces live sensor streams.
- Each tick: one `SensorReading` per zone (16 zones).
- Alert triggers when a zone's risk class **crosses upward** (Safe→Warning, Warning→Evacuation, Safe→Evacuation).
- De-dup logic: identical alerts for the same zone + severity within a cooldown window are suppressed.
- WebSocket broadcasts both `telemetry_update` and `alert_event` envelopes.

### Phase 22 — Frontend Re-pointed

- Frontend `lib/api.ts` and `lib/websocket.ts` updated to point at the real backend URL.
- `types.ts` drift fixed — TypeScript interfaces aligned with actual Pydantic schema field names.

### Phase 23 — Render Deployment

- Backend deployed to: `https://sih2026-xk4z.onrender.com`
- Free tier: sleeps after 15 min of inactivity.
- Cold start: ~30–60 seconds (model loading).

### Phase 24 — Vercel Deployment

- Frontend deployed to: `https://sih-2026-drab.vercel.app`
- Auto-deploys on push to main branch.
- Next.js 16 optimised for Vercel (zero-config).

---

## 10. Integration & Deploy Hardening (Phases 25–29)

### Phase 25 — Zero-Mock Audit

- Grep for any remaining mock/fake data paths in backend code.
- Confirm `model_version` field is populated correctly in all responses.
- Result: clean.

### Phase 26 — Full Integration Test

Using `TestClient` (from `httpx`) and `websocket_connect()`:

- `POST /predict` with known input → correct risk class returned.
- `WS /ws/feed` → receives `telemetry_update` frames.
- **Forced evacuation test:** Inject extreme displacement → `alert_event` received.
- **De-dup test:** Repeat same extreme input within cooldown → second alert suppressed.
- **Reconnect test:** Disconnect WebSocket → client reconnects automatically.

### Phase 27 — Deploy Hardening

- **Debug-flag audit:** Ensure no `DEBUG=True` in production.
- **GitHub Actions heartbeat:** `.github/workflows/keep-render-alive.yml` — cron every 14 minutes pings `GET /health` to prevent Render free-tier cold start.
- **CORS verification:** Confirm frontend origin is in the allowed origins list.
- **WS verification:** Confirm WebSocket upgrade works through Render's reverse proxy.

### Phase 28 — Demo Script + Failure-Mode Rehearsal

- Demo walkthrough scripted.
- Failure modes identified and rehearsed:
  - Backend cold start → heartbeat mitigates.
  - WebSocket disconnect → auto-reconnect in frontend.
  - Model inference slow → timeout handling.

### Phase 29 — End-of-Day-7 Review Checklist

All items cleared. Session notes: `docs/session-done-03.md`.

---

## 11. Model Comparison & Evaluation

### Head-to-Head: Evacuation Class

| Metric | RandomForest (v2) | XGBoost (v2) | GRU |
|---|---|---|---|
| **Precision** | 0.9949 | 0.9704 | 1.0000 |
| **Recall** | 0.9848 | 1.0000 | 0.7208 |
| **F1-Score** | 0.9898 | 0.9850 | 0.8378 |
| **Missed Evacuations** | 3/197 | 0/197 | 55/197 |
| **Terrain/SAR SHAP** | 17.03% | 6.90% | N/A |

### How to Read This Table

- **Precision** = Of all predictions labelled "Evacuation," what fraction were correct? High precision = few false alarms.
- **Recall** = Of all real evacuation events, what fraction did we catch? High recall = few missed events.
- **F1** = Harmonic mean of precision and recall.
- **Missed Evacuations** = The critical safety metric. Lower is always better.
- **Terrain/SAR SHAP** = How much the contextual (non-sensor) features contribute. Higher = model uses geological context, not just sensor readings.

### Production Model Choice

**RF v2** is the production model loaded in the deployed backend. Reasons:

1. Best F1 balance (0.9898) — near-perfect precision with excellent recall.
2. Only 3 missed evacuations out of 197 (1.5% miss rate).
3. Strongest terrain/SAR SHAP contribution (17.03%) — the model genuinely learns from geological context.
4. Fast inference (~1ms per prediction on CPU) — critical for real-time WebSocket streaming.
5. XGBoost's 0 missed evacuations comes at the cost of lower precision (more false alarms).

### GRU's Role

The GRU is not the production model. It's included for **architectural completeness** and **ensemble potential**:

- Its perfect precision means any evacuation it flags is almost certainly real.
- In a production ensemble, GRU could serve as a "confirm" signal: if both RF and GRU say Evacuation, confidence is very high.
- The 55 missed evacuations are all Warning-class — the GRU is conservative, not dangerous.

---

## 12. Data Generation Evolution (v1 → v2c)

This section documents the critical debugging journey that transformed the dataset from unusable (v1) to production-ready (v2).

### v1 — The Broken Baseline

- **Labelling:** `risk_level` based purely on raw `displacement_mm_day` against fixed thresholds.
- **Result:** Terrain (slope, aspect, curvature) and SAR backscatter had zero influence on labels.
- **Crossover pairs:** 0 (no pair of samples where contextual features differ but labels are the same).
- **Model performance:** XGBoost 0.00% SHAP on terrain/SAR, RF 12.27%.
- **Diagnosis:** Tree models had no reason to use contextual features because the label boundary was purely displacement-defined.

### v2 — The Fix (Production)

- **Labelling:** `risk_score = displacement_mm_day × susceptibility_multiplier`.
- `susceptibility_multiplier` is computed from terrain (steep slope, concave curvature) and SAR (high backscatter change).
- Thresholds applied to `risk_score`, not raw displacement.
- **Result:** 75 crossover pairs. Contextual features now influence labels.
- **SHAP:** RF terrain/SAR = 18.63%, XGBoost = 6.75%.
- **This is the production dataset.**

### v2b — Isolation Test (Multiplier Alone, Original Range)

- Tests whether the multiplier alone (without range widening) drives SHAP contribution.
- **Result:** 0 crossover pairs, XGBoost 0.00%, RF 30.31%.
- **Insight:** RF is more sensitive to structural features; XGBoost needs explicit crossover signal.

### v2c — Isolation Test (Multiplier Alone, Aggressive Range)

- Same as v2b but with a wider multiplier range.
- **Result:** 3 crossover pairs, XGBoost 0.00%, RF 30.31%.
- **Insight:** Range widening alone doesn't fix XGBoost. The crossover pairs in v2 are the key.

### Summary Table

| Version | Crossover Pairs | XGBoost Terrain/SAR SHAP | RF Terrain/SAR SHAP | Status |
|---|---|---|---|---|
| v1 | 0 | 0.00% | 12.27% | Broken |
| **v2** | **75** | **6.75%** | **18.63%** | **Production** |
| v2b | 0 | 0.00% | 30.31% | Isolation test |
| v2c | 3 | 0.00% | 30.31% | Isolation test |

---

## 13. Frontend Design & Architecture

### Design Philosophy

**Quiet, Precise, Grounded.** The frontend is a safety-critical monitoring tool, not a marketing page. Every design decision prioritises clarity and reduces cognitive load for operators who may be under stress.

### Visual Language

- **Theme:** Light mode only. No dark mode (safety dashboards in well-lit control rooms).
- **Primary accent:** Ink-blue `#2563EB` — conveys trust, precision, calm.
- **Background:** Paper white — clean, low-fatigue for extended monitoring.
- **Typography:** Geist family (sans for body, mono for data readouts).
- **Layout pattern:** Row-based, not card grids. Rows of data feel more like a control panel; card grids feel like a portfolio site.

### Responsive Design

- Breakpoints: 320px (mobile) to 1440px (desktop control room).
- All pages tested across the full range.

### Pages

| Route | Purpose | Key Components |
|---|---|---|
| `/` | Home / landing | Project overview, quick stats |
| `/dashboard` | 3D pit heatmap | MapLibre GL 3D, zone colouring by risk, summary metric cards |
| `/alerts` | Real-time alert log | WebSocket-fed alert stream, severity badges, acknowledgement UI |
| `/trends` | Telemetry trends | Recharts line charts (displacement, rainfall, SAR over time) |
| `/pitch` | Pitch companion | 996-line presentation UI, AriaTab RAG chat interface |

### Key Components

- **`TopBar.tsx`** — Global navigation, responsive hamburger on mobile.
- **`PitHeatmap.tsx`** — MapLibre GL component rendering the 4×4 zone grid as a 3D extruded heatmap, coloured by risk level. Uses the `style.json` map style.
- **`TrendChart.tsx`** — Recharts wrapper for time-series visualisation. Supports multi-line, tooltips, zoom.

### Frontend Design Guide

A comprehensive 450-line design guide is maintained in `frontend.md` at the repo root. It covers:

- Colour tokens and usage rules.
- Typography scale.
- Component patterns.
- Spacing and layout grid.
- Animation and transition guidelines.

---

## 14. API Reference

### GET /health

**Purpose:** Liveness probe and service identification.

**Response:**
```json
{
  "status": "healthy",
  "model_version": "rf-v2-20260820",
  "service": "rockfall-prediction"
}
```

**Used by:** GitHub Actions heartbeat (keep-render-alive.yml) every 14 minutes.

---

### POST /predict

**Purpose:** Run a single sensor reading through the ML model and return a risk prediction.

**Request body:** `SensorReading` (see [Data Schemas](#15-data-schemas)).

**Response:** `RiskPrediction` (see [Data Schemas](#15-data-schemas)).

**Example:**
```json
// Request
{
  "sensor_id": "sensor-07",
  "zone_id": "zone-12",
  "timestamp": "2026-08-15T10:30:00Z",
  "displacement_mm_day": 85.2,
  "vibration": 0.42,
  "pore_pressure": 310.5,
  "strain": 0.0034,
  "rainfall_mm": 12.8,
  "risk_level": null
}

// Response
{
  "zone_id": "zone-12",
  "timestamp": "2026-08-15T10:30:00Z",
  "risk_level": "warning",
  "risk_score": 0.73,
  "displacement_velocity_mm_day": 85.2,
  "model_version": "rf-v2-20260820"
}
```

---

### WS /ws/feed

**Purpose:** Real-time telemetry and alert streaming via WebSocket.

**Protocol:** `ws://` or `wss://` (upgrade from HTTP).

**Message types:**

#### telemetry_update
```json
{
  "type": "telemetry_update",
  "data": {
    "sensor_id": "sensor-03",
    "zone_id": "zone-05",
    "timestamp": "2026-08-15T10:30:00Z",
    "displacement_mm_day": 12.4,
    "vibration": 0.18,
    "pore_pressure": 205.0,
    "strain": 0.0012,
    "rainfall_mm": 3.2,
    "risk_level": "safe"
  }
}
```

#### alert_event
```json
{
  "type": "alert_event",
  "data": {
    "alert_id": "alert-20260815-103000-zone12",
    "zone_id": "zone-12",
    "severity": "evacuation",
    "message": "Risk escalated to EVACUATION in zone-12. Immediate action required.",
    "triggered_at": "2026-08-15T10:30:00Z",
    "acknowledged": false
  }
}
```

**Alert trigger logic:** An `alert_event` is emitted when a zone's risk class crosses upward (Safe→Warning, Warning→Evacuation, or Safe→Evacuation). Duplicate alerts for the same zone + severity within a cooldown window are suppressed.

---

## 15. Data Schemas

### SensorReading

```typescript
interface SensorReading {
  sensor_id: string;          // e.g. "sensor-07"
  zone_id: string;            // e.g. "zone-12"
  timestamp: string;          // ISO 8601
  displacement_mm_day: number; // Daily displacement in mm
  vibration: number;          // Normalised vibration index
  pore_pressure: number;      // kPa
  strain: number;             // Microstrain
  rainfall_mm: number;        // Daily rainfall in mm
  risk_level?: string | null; // Optional override (usually null, model predicts)
}
```

### RiskPrediction

```typescript
interface RiskPrediction {
  zone_id: string;
  timestamp: string;                  // ISO 8601
  risk_level: "safe" | "warning" | "evacuation";
  risk_score: number;                 // 0.0 – 1.0
  displacement_velocity_mm_day: number;
  model_version: string;              // e.g. "rf-v2-20260820"
}
```

### AlertEvent

```typescript
interface AlertEvent {
  alert_id: string;                   // Unique, timestamped
  zone_id: string;
  severity: "warning" | "evacuation";
  message: string;                    // Human-readable
  triggered_at: string;               // ISO 8601
  acknowledged: boolean;              // Default false
}
```

---

## 16. Deployment Architecture

### Overview

```
┌──────────────┐       ┌──────────────┐
│   Vercel     │       │   Render     │
│   (Frontend) │──────▶│   (Backend)  │
│   Next.js 16 │  HTTP │   FastAPI    │
│              │◀──────│   + WS       │
└──────────────┘       └──────┬───────┘
                              │
                    ┌─────────▼─────────┐
                    │  GitHub Actions    │
                    │  (Heartbeat cron)  │
                    │  every 14 min      │
                    └───────────────────┘
```

### Backend (Render)

- **Platform:** Render free tier.
- **Runtime:** Python 3.12, uvicorn.
- **Sleep behaviour:** After 15 minutes of inactivity.
- **Cold start:** ~30–60 seconds (loads RF model into memory).
- **Mitigation:** GitHub Actions cron pings `GET /health` every 14 minutes.
- **Config:** `render.yaml` + `runtime.txt`.

### Frontend (Vercel)

- **Platform:** Vercel (hobby tier).
- **Framework:** Next.js 16.3.1, optimised for Vercel.
- **Deploy trigger:** Push to main branch (auto-deploy).
- **Environment variables:** Backend URL configured via Vercel env vars.

### Heartbeat

**File:** `.github/workflows/keep-render-alive.yml`

```yaml
# Simplified structure
on:
  schedule:
    - cron: '*/14 * * * *'  # Every 14 minutes
jobs:
  keep-alive:
    runs-on: ubuntu-latest
    steps:
      - name: Ping backend
        run: curl -s https://sih2026-xk4z.onrender.com/health
```

This prevents the Render free-tier instance from sleeping due to inactivity.

---

## 17. Edge Deployment (Optional)

**Priority:** Low. Buildable artifact if time allows.

### Architecture

```
Sensors → Edge Device (Raspberry Pi) → ONNX Runtime → Local Alert
```

### Why ONNX Over TFLite

- **Performance:** ONNX Runtime is faster on ARM CPUs (Raspberry Pi 4/5).
- **Format unification:** One format covers both XGBoost (tree ensembles) and PyTorch (GRU). TFLite would require separate conversion pipelines.
- **Ecosystem:** ONNX has better tooling for scikit-learn → ONNX conversion (sklearn-onnx).

### What's Needed

1. Convert RF v2 model to ONNX (`skl2onnx`).
2. Convert GRU to ONNX (`torch.onnx.export`).
3. Write a Python inference script that reads sensor data, runs ONNX, outputs alerts.
4. Deploy to Raspberry Pi with a cellular/WiFi link for local SMS/buzzer alerts.

### Current State

- Conversion scripts not yet written.
- No physical hardware confirmed (designed for Pi/Jetson, no access yet).

---

## 18. Test Suite

| Test File | What It Covers |
|---|---|
| `test_alert_dedup.py` | Alert de-duplication logic — same zone + severity within cooldown suppressed |
| `test_physics_sanity.py` | Physics generator produces valid displacement ranges, correct acceleration |
| `test_predict_endpoint.py` | `POST /predict` — valid input → valid RiskPrediction, schema compliance |
| `test_ws_disconnect.py` | WebSocket disconnect handling — clean close, no server crash |
| `test_ws_feed.py` | WebSocket feed — receives telemetry_update frames |
| `test_ws_phase21.py` | Phase 21 integration — real model + real generator via WS |

### Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

### Test Philosophy

Tests focus on **integration contracts** — does the API return the right schema? Does the WebSocket deliver frames? Does the alert logic trigger correctly? Unit tests for individual ML models are less critical than end-to-end behaviour verification.

---

## 19. Open Questions & Unresolved Items

### Twilio SMS Alerts

- **Status:** Unconfirmed.
- **Blockers:** Budget not allocated, API keys not provisioned.
- **Architecture if implemented:** Backend triggers Twilio API call when `alert_event` severity is "evacuation." Phone numbers stored per-zone or per-worker.
- **Priority:** Medium. Would complete the alert chain from prediction → human notification.

### Edge Hardware

- **Status:** Designed for Raspberry Pi / Jetson, but no physical hardware confirmed.
- **Blockers:** Budget, procurement timeline.
- **Current capability:** ONNX conversion scripts not written. Architecture is sound but untested on real hardware.

### Production Sensor Data

- **Current state:** All sensor data is synthetic (generated by `physics_generator.py`).
- **Honesty:** The system is designed and tested to work with real sensor data, but we have not connected physical IoT sensors. The synthetic data is physics-informed (Fukuzono model) and realistic, but it is not real.
- **What would change:** Replace the generator with an MQTT/HTTP ingestion endpoint that receives data from physical sensors. The ML pipeline, API, and frontend would require zero changes.

---

## 20. Operating Instructions & Conventions

### Code Standards

- **Real runnable code, not pseudocode.** Every script in `scripts/` is executable.
- **Copy-paste ready output.** Terminal commands, code snippets, and API examples are directly usable.
- **One clarifying question when genuinely ambiguous.** Prefer action over endless clarification loops.
- **Search web for time-sensitive info.** Don't rely on training data for current API versions, library changes, or deployment platform quirks.

### Data Honesty

Be upfront about data provenance:

- **Synthetic:** Sensor data (`synthetic_sensors*.csv`, live generator output).
- **Real:** DEM terrain derivatives (Copernicus GLO-30), SAR backscatter (Sentinel-1), rainfall (Open-Meteo ERA5), zone grid (digitised over real mine footprint).

### Git Conventions

- Don't commit secrets or API keys.
- Don't auto-push unless explicitly asked.
- Inspect `git diff` before staging.
- Use conventional commit messages when committing.

### AI Agent Directives

See `AGENTS.md` for the full operational protocol. Key points:

- Minimal, surgical diffs.
- No stubs, no placeholders, no `TODO` in production code.
- Verify outputs are valid and non-empty.
- Run lint and typecheck after changes.

---

## 21. Pitch Framing & Defence Notes

This section contains the narrative framing for the SIH presentation and anticipated challenges from judges.

### Core Narrative

> SSR is the gold standard for slope monitoring — but it costs $250k–$500k per unit and only covers line-of-sight. Our system fuses cheaper, distributed data sources (satellite SAR, terrain models, weather, IoT sensors) into an ML pipeline that extends rockfall risk prediction to zones where full radar isn't affordable. We don't replace SSR — we extend the safety perimeter.

### Key Defence Points

#### "Your model just predicts 'safe' all the time."

**Rebuttal:** Our evaluation uses per-class precision and recall, not accuracy. The Evacuation class F1 is 0.9898 (RF) and 0.9850 (XGBoost). If the model predicted only "safe," Evacuation recall would be 0.00 and F1 would be 0.00. We show confusion matrices with real numbers. The model genuinely discriminates between all three classes.

#### "You're using synthetic data."

**Rebuttal:** Yes, and we're honest about it. The synthetic data is generated using the Fukuzono (1985) inverse velocity model — the same physics used in real SSR systems. The terrain, SAR, and rainfall data are real (Copernicus, Sentinel-1, Open-Meteo). The synthetic component is the sensor stream, which would be replaced by real IoT sensors in production. The choice to use synthetic data is defensible because:
1. Real mine sensor datasets are proprietary and unavailable for hackathons.
2. Physics-informed synthesis ensures realistic displacement acceleration patterns.
3. The ML pipeline is agnostic to data source — swapping in real sensors requires zero model changes.

#### "Why not InSAR? SAR backscatter is low resolution."

**Rebuttal:** We use Sentinel-1 GRD **amplitude backscatter**, not InSAR (interferometric phase). InSAR requires precise co-registration, atmospheric correction, and has decorrelation issues in vegetated or steep terrain. Backscatter is more robust as a contextual feature — it correlates with surface roughness, moisture, and disturbance. It's a proxy, not a displacement measurement, and the model uses it as one feature among many.

#### "Why class weighting over SMOTE?"

**Rebuttal:** SMOTE synthesises new samples by interpolating between existing minority-class neighbours. In our dataset, features are physically correlated — displacement autocorrelates over time, rainfall has seasonality, SAR backscatter changes slowly. SMOTE would create physically impossible feature combinations (e.g., high displacement with low rainfall and anomalous SAR in a way that can't occur in reality). Class weighting preserves every real sample's physical integrity.

#### "Why RF over XGBoost? XGBoost has 0 missed evacuations."

**Rebuttal:** XGBoost's perfect recall comes at the cost of lower precision (0.9704 vs RF's 0.9949). In a safety system, false alarms erode operator trust — if every alert is a false alarm, workers stop responding. RF's 3 missed evacuations (1.5% miss rate) is acceptable when weighed against significantly fewer false alarms. In production, an ensemble of both models could provide the best of both worlds.

#### "Why include the GRU if tree models are better?"

**Rebuttal:** Architectural completeness and ensemble potential. The GRU processes the same data as a 14-day temporal sequence, capturing acceleration patterns that tree models see as flat feature vectors. Its perfect precision (1.0) means any evacuation it flags is almost certainly real. In a production ensemble, GRU could serve as a "confirm" signal for high-confidence alerting.

#### "What's the alert lead time?"

**Rebuttal:** Our reference architecture (IEEE paper) reports ~30-minute mean alert lead time with a hybrid CNN-LSTM ensemble. Our system's lead time depends on the physics generator tick rate (configurable) and the model's ability to detect the onset of acceleration. In the synthetic test data, the model detects evacuation-risk patterns with high accuracy across the 14-day window.

### Pitch Companion App

A dedicated `/pitch` page in the frontend provides a 996-line interactive presentation companion with:
- Live data visualisations.
- AriaTab RAG chat for Q&A during the pitch.
- Key metrics and model comparison tables.

---

## 22. Glossary

| Term | Definition |
|---|---|
| **SSR** | Slope Stability Radar — ground-based radar for sub-mm displacement monitoring of pit walls |
| **SAR** | Synthetic Aperture Radar — satellite radar imaging (Sentinel-1) |
| **GRD** | Ground Range Detected — Sentinel-1 product type (amplitude, not phase) |
| **InSAR** | Interferometric SAR — uses phase difference for displacement measurement (we do NOT use this) |
| **Backscatter** | Radar signal reflected back from the surface; proxy for roughness, moisture, disturbance |
| **VV / VH** | Vertical-Transmit/Vertical-Receive and Vertical-Transmit/Horizontal-Receive polarisations |
| **DEM** | Digital Elevation Model — 3D terrain surface |
| **GEE** | Google Earth Engine — cloud platform for geospatial analysis |
| **Fukuzono (1985)** | Inverse velocity model for predicting slope failure time |
| **SHAP** | SHapley Additive exPlanations — model interpretability method |
| **GRU** | Gated Recurrent Unit — recurrent neural network architecture for sequence modelling |
| **ONNX** | Open Neural Network Exchange — interoperable ML model format |
| **Crossover pair** | Two samples with similar sensor readings but different labels due to contextual feature influence |
| **Class weighting** | Technique to handle imbalanced classes by assigning higher loss weight to minority class |
| **SMOTE** | Synthetic Minority Oversampling Technique — generates synthetic minority samples (we avoid this) |
| **Temporal split** | Train/val/test split by time, not random shuffle — prevents data leakage |
| **Sample weight** | Per-sample multiplier applied to the loss function during training |
| **Susceptibility** | Zone-level measure of geological instability (derived from terrain + SAR) |
| **Risk score** | Composite metric: `displacement × susceptibility_multiplier` |
| **Cold start** | Render free-tier instance sleeping after idle period; ~30–60s restart time |
| **Heartbeat** | Scheduled HTTP ping to prevent cold start (GitHub Actions cron) |
| **AriaTab** | Accessible tab component used in the pitch companion UI |

---

## Appendix: Phase Completion Summary

| Phase Group | Phases | Status | Session Doc |
|---|---|---|---|
| Data Pipeline | 1–9 | ✅ Done | `session-done-01.md` |
| ML Baseline | 10–16 | ✅ Done | `session-done-02.md` |
| Deep Learning + Backend | 17–24 | ✅ Done | `session-done-03.md` |
| Integration & Hardening | 25–29 | ✅ Done | (inline in session-done-03.md) |

**Total phases completed:** 29/29.

---

*This document is the canonical reference for the SIH25071 project. When in doubt, this file is the source of truth. Update it as the project evolves.*
