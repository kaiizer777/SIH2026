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
| **API Docs** | `https://sih2026-xk4z.onrender.com/docs` (auto-generated OpenAPI) |
| **License** | MIT |

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
| **Next.js** | 16.3.1 | App Router, React Server Components, Turbopack dev server |
| **React** | 19.2.x | Latest stable |
| **Node.js** | ≥20.9 | Required by Next.js 16 |
| **TypeScript** | 5.9.3 | Held back from TS7 (eslint-config-next not yet compatible) |
| **ESLint** | 9.x | Held back from v10 (same reason) |
| **Tailwind CSS** | 4.x | CSS-first config, `@theme` inline |
| **recharts** | 3.10.1 | Telemetry trend charts |
| **maplibre-gl** | 6.4.1 | MIT-licensed, no API key required |
| **react-map-gl** | 8.1.2 | React wrapper for MapLibre |
| **Playwright** | 1.62.1 | E2E testing (devDependency) |

### Backend

| Technology | Version | Notes |
|---|---|---|
| **FastAPI** | 0.141.x | Async Python web framework |
| **uvicorn** | latest | ASGI server |
| **Python** | 3.12 | Pinned in runtime.txt |
| **Pydantic** | v2 | Schema validation (bundled with FastAPI) |
| **python-dotenv** | latest | `.env` file loading (`load_dotenv()`) |
| **sentry-sdk** | 2.68.0 | Error monitoring (optional, DSN via env var) |
| **websockets** | 17.0.1 | WebSocket client library (for testing/probes) |

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

- **Mine type:** Open-pit coal mine.
- **Bounding box** (from `data/aoi.json`):
  - SW corner: 22.3204°N, 82.6476°E
  - NE corner: 22.342°N, 82.6882°E
  - Centre: 22.3312°N, 82.6679°E
- **Provenance:** Coordinates derived from OpenStreetMap way 136512819 (`landuse=quarry`).
- Selected for: operational open-pit mine, existing SSR deployment (real-world validation reference), freely available satellite coverage.
- Confirmed compatible with the SSR/Kusmunda pitch framing.

### Phase 2 — GEE + Cloud Auth

- **GEE project ID:** `sih25071-rockfall`.
- Google Earth Engine Python API authenticated via `ee.Authenticate()` + `ee.Initialize(project='sih25071-rockfall')`.
- Dependencies: `earthengine-api`, `richdem`, `rasterio`, `numpy`, `pandas`.
- `richdem` verified working in WSL2 `~/geo-env` (Python 3.10) and Windows `backend/venv`.
- Verification script: `backend/scripts/verify_gee.py`.

### Phase 3 — DEM Pull + Terrain Derivatives

- **Source:** Copernicus GLO-30 digital elevation model via GEE.
- **Output files:**
  - `data/dem.tif` — raw elevation.
  - `data/slope.tif` — slope angle (degrees), computed via richdem.
  - `data/aspect.tif` — slope aspect (degrees from north).
  - `data/curvature.tif` — profile curvature (concavity/convexity).
- **Processing:** GEE export to Google Cloud Storage → local download → richdem terrain analysis.
- **Sanity check:** Visual verification in `data/terrain_sanity_check.png` (matplotlib slope/aspect plot confirming bench geometry).

### Phase 4 — SAR Backscatter Extraction

- **Source:** Sentinel-1 GRD (COPERNICUS/S1_GRD), C-band SAR.
- **Mode:** DESCENDING, Track 19 (relative orbit). `instrumentMode = 'IW'` (Interferometric Wide swath).
- **Polarisations:** VV and VH.
- **Acquisitions:** 30 dates (2025-08-19 to 2026-08-19).
- **Output:** `data/sar_backscatter.csv` — VV and VH mean backscatter per zone per date (columns: `date, zone_id, vv_backscatter, vh_backscatter`).
- **Important distinction:** This is **amplitude backscatter** (surface reflectivity), not InSAR (interferometric phase). Backscatter changes correlate with surface disturbance, moisture, and roughness — useful as a contextual feature but not a displacement measurement.

### Phase 5 — Rainfall Data

- **Source:** Open-Meteo Historical Archive API (ERA5 reanalysis).
- **Period:** 356 daily records (2025-08-22 to 2026-08-12). Note: SAR dates (2025-08-19 to 2026-08-19) and rainfall dates (2025-08-22 to 2026-08-12) are not perfectly aligned — the join handles this via date matching.
- **Spatial scale caveat:** ERA5-Land reanalysis resolution (~9–11 km) exceeds the pit footprint (4.8 km diagonal). One AOI center point query is optimal — zero variance across zone centroids was confirmed.
- **Output:** `data/rainfall.csv` — daily precipitation in mm.
- **Cross-validation:** 100% alignment with 30 SAR acquisition dates confirmed; zero missing/null records.

### Phase 6 — Zone Feature Table

- **Zone grid:** 4×4 = 16 zones defined in `data/zone_grid.json` (GeoJSON polygons over the mine footprint, created 2026-08-19T17:18:43).
- **Zone-tier distribution** (from terrain/SAR susceptibility scoring):
  - 10 Low-risk zones (62.5%)
  - 4 Medium-risk zones (25.0%)
  - 2 High-risk zones (12.5%)
  - Top 2 zones by susceptibility → evacuation tier, next 4 → warning tier, rest → safe tier.
- **Output:** `data/zone_features.csv` — 480 rows (16 zones × 30 SAR dates).
- **Columns:** zone_id, date, slope, aspect, curvature, vv_backscatter, vh_backscatter, rainfall_mm.

### Phase 7 — Synthetic Sensor Data

The most nuanced dataset. See [Section 12](#12-data-generation-evolution-v1--v2c) for the full evolution story.

- **Generator:** `backend/app/physics_generator.py` — implements Fukuzono (1985) inverse velocity model.
- **Fukuzono formula:** `v_fukuzono = 25.0 / (dt_to_failure ** 0.25)` where `dt_to_failure` is days until peak failure time.
- **Peak failure day:** `_T_PEAK_FAILURE = 338` (day 338 = 2026-07-25, late monsoon maximum).
- **API lambda decay:** 0.82.
- **Susceptibility scoring weights:** slope × 0.50 + curvature × 0.30 + SAR × 0.20.
- **Susceptibility multiplier range:** [0.70, 1.30] (rescaled from [0, 1] susceptibility composite).
- **Staggered initial offsets:** zone_01 at t=0, zone_02 at t=1, ..., zone_16 at t=15.
- **Simulated timestamps:** Use rainfall.csv dates (not wall-clock). Series wraps at mod 356.
- **Inter-sensor correlations** (validated against calibration datasets):
  - pore_pressure–displacement: r=0.918
  - strain–displacement: r=0.968
  - vibration–displacement: r=0.970
- **Parameters per zone:** susceptibility (from terrain/SAR), noise floor, acceleration profile, v_base, v_rain_amp, u_base, u_gain (per tier).
- **Output (v2 — production):** `data/synthetic_sensors.csv` — 5,696 rows (16 zones × 356 days).
- **Columns:** sensor_id, zone_id, timestamp, displacement_mm_day, vibration, pore_pressure, strain, rainfall_mm, risk_level.
- **Labelling logic (v2):**
  1. Compute `risk_score = displacement × susceptibility_multiplier`.
  2. Apply thresholds on `risk_score` (not raw displacement).
  3. This produces physically meaningful class boundaries that interact with terrain context.
- **Target class distribution** (from 2026 physics-informed rockfall paper): Low 60% / Medium 25% / High 15%. Actual achieved: 60.13% / 24.98% / 14.89%.

**v1 bug:** Labels were purely displacement-based; terrain and SAR features were contextual only and never influenced the label. This led to 0 crossover pairs and near-zero tree-model SHAP importance for contextual features.

**v2 fix:** The `risk_score` composite ensures that the same raw displacement produces different risk labels depending on zone susceptibility (steep, unstable terrain escalates risk).

### Phase 8 — Backend Mock Stability Check

- Verified that the FastAPI app starts cleanly with mock data paths.
- Confirmed schema validation round-trip.
- **Zone ID drift fix:** `rockfall.py` line 78 had placeholder zone IDs (`["ZONE-A", "ZONE-B", "ZONE-C", "PIT-NORTH"]`). Fixed to `[f"zone_{i:02d}" for i in range(1, 17)]` — now matches the canonical `zone_01..zone_16` format across all data files and backend schema.

### Phase 9 — End-of-Day-2 Review

- All data assets inventoried.
- Pipeline reproducibility confirmed.
- **Schema drift finding:** `frontend/lib/types.ts` `SensorReading` was missing the optional `risk_level?: RiskLevel | null` field. Non-blocking on Day 2, flagged for Phase 22 fix.
- Session notes: `docs/session-done-01.md`.

---

## 7. ML Pipeline (Phases 10–16)

All phases complete.

### Phase 10 — Temporal Split

**Zero temporal leakage.** Data is split by date, not randomly:

| Split | Date Range | Rows | Days | Evacuation Count |
|---|---|---|---|---|
| **Full dataset** | 2025-08-22 → 2026-08-12 | 5,696 | 356 | 741 (13.0%) |
| **Train (full)** | 2025-08-22 → 2026-06-02 | 4,560 | 285 | 544 (12.0%) |
| **Train (core)** | 2025-08-22 → 2026-04-06 | 3,648 | 228 | — |
| **Validation** | 2026-04-07 → 2026-06-02 | 912 | 57 | 113 (12.4%) |
| **Test** | 2026-06-03 → 2026-08-12 | 1,136 | 71 | 197 (17.3%) |

- **train_full** (4,560 rows): used for class weight computation (`compute_sample_weight`).
- **train_core** (3,648 rows): used for actual model training. The difference (912 rows) is the validation period used for early stopping / hyperparameter tuning.
- Test set has higher evacuation density (17.3%) because late-monsoon displacement peaks fall in the test window.

Metadata stored in `data/split_metadata.json`.

### Phase 11 — Class Weighting

- **Method:** `sklearn.utils.class_weight.compute_sample_weight('balanced')`.
- **Balanced effective weights:** ~0.53 (safe) / 1.29 (warning) / 2.84 (evacuation). These are inverse-frequency multipliers — evacuation samples get ~5.4× the loss weight of safe samples.
- **Why not SMOTE:** Synthetic Minority Oversampling Technique generates synthetic samples by interpolating between existing minority-class neighbours. In our data, features are **physically correlated** across time (displacement is autocorrelated, rainfall has seasonality, SAR backscatter changes slowly). SMOTE would create physically impossible feature combinations — a zone cannot have high displacement, low rainfall, and high SAR backscatter simultaneously in a way that's plausible. Class weighting preserves the physical structure of every real sample.
- **Pitch one-liner (memorise verbatim):** *"We use class-weighted loss rather than SMOTE because our sensor channels are physically correlated by construction — synthetic interpolation risks generating physically implausible readings. Weighting keeps every training point real."*
- **Output:** `data/train_sample_weights.npy` (and v2b/v2c variants).
- **Metadata:** `data/weights_metadata.json`.

### Phase 12 — Model Training

**Feature join:** SAR/terrain features forward-filled onto daily sensor rows. **Max forward-fill staleness:** 23 days worst-case (within 1 SAR repeat-pass cycle — defensible). Mean staleness: 5.84 days, median: 6.00 days.

**RandomForest (v2 — production):**
- `n_estimators=300`
- Scikit-learn implementation
- Class-weighted via sample_weight parameter

**XGBoost (v2 — production):**
- `n_estimators=300`
- `max_depth=6`
- `learning_rate=0.1`
- Class-weighted via sample_weight parameter

Both trained on v2 data with temporal split and sample weights.

### Phase 13 — SHAP Analysis

SHAP (SHapley Additive exPlanations) values computed on the **validation set** (912 rows).

**Key result (v2, validation set):**

| Model | Terrain + SAR SHAP Contribution |
|---|---|
| RandomForest | 18.63% |
| XGBoost | 6.75% |

**Test set SHAP** (out-of-sample, reported in the comparison table below): RF 17.03%, XGBoost 6.90%. Numbers align perfectly with validation — no material divergence.

This confirms that contextual features (terrain derivatives + SAR backscatter) contribute meaningfully to predictions — a direct consequence of the v2 labelling fix where `risk_score` incorporates zone susceptibility.

**v1 comparison:** RF terrain/SAR SHAP was 12.27%, XGBoost was near-zero. The v2 fix improved feature utilisation.

**Validation accuracy:** RF 100%, XGBoost 99.89% (1 misclassification on 912 rows). Both essentially perfect on synthetic data — expected.

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
- Feature order: `feature_order.json` — **exact column order matters at inference time:**
  ```
  displacement_mm_day, vibration, pore_pressure, strain, slope, aspect, curvature, vv_backscatter, vh_backscatter, rainfall_mm
  ```
- Label encoding: `label_encoding.json` — `{"safe": 0, "warning": 1, "evacuation": 2}` (maps string label ↔ numeric class).

### Phase 16 — Review Checklist

All items cleared. Session notes: `docs/session-done-02.md`.

---

## 8. Deep Learning (Phases 17–19)

All phases complete.

### Phase 17 — GRU Sequence Framing

- **Window size:** 14 days (each input is a 14-timestep × 10-feature tensor).
- **Stride:** 1 day (sliding window).
- **History boundary policy (Option B):** Windows may pull history **backward** from an earlier split (e.g., a val-target window can reach into train-period dates for its preceding 13 days) but **never forward** into a later split. Label/split assignment follows the **target (last-timestep) date only**. This recovers the first 13 days of evacuation signal in val/test at zero leakage cost.
- **Sequence counts:**
  - Train: 3,440 sequences (lower than 4,560 train rows because each zone's first 13 days have no earlier history to borrow from — genuinely dropped, not a bug)
  - Validation: 912 sequences
  - Test: 1,136 sequences
- **Evacuation-class sequence counts:** train 403, val 113, test 197 — all above the thin-class warning threshold (30).
- **Storage:** `data/sequences/*.npz` with manifest in `data/sequences/manifest.json`.

### Phase 18 — GRU Training

- **Architecture:** Single-layer GRU.
  - `input_size=10` (features per timestep)
  - `hidden_size=64`
  - `num_classes=3`
  - `dropout=0.2` (between GRU output and linear layer)
- **Framework:** PyTorch (verified 2.11.0+cpu).
- **Loss:** Class-weighted `nn.CrossEntropyLoss(weight=weight_tensor)` with weights `[0.5341, 1.2884, 2.8453]` computed from `y_train_seq` (3,440 labels, not the full 4,560 row-level labels — sequence class distribution differs slightly).
- **Why GRU over LSTM:** At ~3,440 training sequences with a short 14-day window on physics-clean synthetic data, GRU's ~25% fewer parameters means less overfitting risk with no accuracy trade-off. LSTM's extra forget/output gating pays off mainly on long or noisy sequences, which this data doesn't have. Literature consensus: GRU is the default starting point when data is limited.
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
- **ConnectionManager pattern:** `app/routers/rockfall.py` implements a `ConnectionManager` class with `connect()`, `disconnect()`, and `broadcast()` methods. Disconnect-safe: per-connection try/except in broadcast loop catches `WebSocketDisconnect`, removes from `active_connections` set, and continues broadcasting to remaining clients.
- Round-robin: **one zone per tick**, not all 16. Full cycle = 16 ticks × 2.5s = 40 seconds.
- Broadcast interval: 2.5 seconds (configurable via `BROADCAST_INTERVAL_SECONDS` env var).
- Physics cursor advances regardless of client count.
- **`classify_alert()` transition table:**
  - Safe→Warning: `"warning"` alert
  - Warning→Evacuation: `"evacuation"` alert
  - Safe→Evacuation: `"evacuation"` alert
  - Evacuation→Warning: `"advisory"` alert (downgrade)
  - Warning→Safe: `"advisory"` alert (downgrade)
  - Same→Same: `None` (suppressed — de-dup)
- WebSocket broadcasts both `telemetry_update` and `alert_event` envelopes.
- **Lifespan-based model loading:** Model loaded in FastAPI's `lifespan` async context manager (not at import time or inside endpoint). Load failure crashes startup (fail-fast) so Render's process manager flags it. This is a deliberate engineering maturity signal — a worker that can't load the model should not serve 500s silently.

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

Using `TestClient` (from `fastapi.testclient`) and `websocket_connect()`:

- **Tick budget:** 32 ticks at `BROADCAST_INTERVAL_SECONDS=0.25s`. Total test duration: 13.12s. Time-to-first-message: 2.69s.
- **Results:** 25 `telemetry_update` envelopes (Pydantic-validated against `SensorReading` + `RiskPrediction`) + 7 `alert_event` envelopes (validated against `AlertEvent`). All schema-valid.
- `POST /predict` with known input → correct risk class returned.
- `WS /ws/feed` → receives `telemetry_update` frames.
- **Forced evacuation test:** `FORCE_EVAC_ZONE=zone_01` env var injects a deterministic evacuation-tier reading (`disp=240 mm/day, vib=0.85, pore=230 kPa, strain=1400`). Alert fired at message index 1 (within 2.69s).
- **De-dup test:** 8 consecutive forced-evac ticks → exactly 1 AlertEvent fired (tick 1), 0 alerts on ticks 2–8. `classify_alert()` correctly returned `None` for `("evacuation", "evacuation")` transitions.
- **Reconnect test:** Opens WS1 (5 messages), closes, sleeps 0.6s, opens WS2 (5 messages). No leak, no duplicate broadcast, WS2 receives fresh ticks normally.
- **Debug env vars (OFF by default, strip before demo):** `FORCE_EVAC_ZONE`, `BROADCAST_FORCE_ZONE_ID`, `BROADCAST_INTERVAL_SECONDS`.

### Phase 27 — Deploy Hardening

- **Debug-flag audit:** Confirmed `render.yaml` contains only `PYTHON_VERSION=3.12.0` and `FRONTEND_ORIGIN`. None of the debug env vars are in production config.
- **GitHub Actions heartbeat:** `.github/workflows/keep-render-alive.yml` — cron every 14 minutes + `workflow_dispatch` for manual demo-day warm-up. Error handling: captures HTTP status + body, fails loudly on non-200.
- **CORS verification:** Backend CORS allow-list includes `https://sih-2026-drab.vercel.app` literally and `https://.*\.vercel\.app` via regex.
- **Live network probe results (2026-08-20 ~08:30 IST):**

| Probe | Result | Detail |
|---|---|---|
| `GET /health` | 200 OK | `{"status":"ok","model_version":"rf-v2-20260820","service":"rockfall-prediction-backend"}` |
| `GET /` | 200 OK | status: online, uptime tick running |
| `POST /predict` | 200 OK | Valid SensorReading → RiskPrediction with `model_version=rf-v2-20260820` |
| `wss://.../ws/feed` | Streaming | TLS+WS handshake ~589ms; 3 telemetry_update envelopes with correct model_version |
| Vercel `/alerts` | 200 OK | WebSocket connected, real alerts rendered |
- **Vercel stale build finding:** Deployed alerts page had 4 hardcoded `mockAlerts` (from pre-Phase-25 commit). Source is clean; fix requires commit + push to trigger Vercel auto-deploy.

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

- **Labelling:** `risk_level` based purely on raw `displacement_mm_day` against fixed thresholds (safe 0–52, warning 50–119, evacuation 120–255 mm/day — hard-clipped, non-overlapping).
- **Class distribution:** 60.3% safe / 24.7% warning / 14.9% evacuation.
- **Result:** Terrain (slope, aspect, curvature) and SAR backscatter had zero influence on labels.
- **Crossover pairs:** 0 (no pair of samples where contextual features differ but labels are the same).
- **Model performance:** XGBoost 0.00% SHAP on terrain/SAR, RF 12.27%.
- **Diagnosis:** Tree models had no reason to use contextual features because the label boundary was purely displacement-defined.

### v2 — The Fix (Production)

- **Labelling:** `risk_score = displacement_mm_day × susceptibility_multiplier`.
- `susceptibility_multiplier` is computed from terrain (steep slope, concave curvature) and SAR (high backscatter change), rescaled [0,1]→[0.70, 1.30].
- **Displacement ranges (overlapping):** safe 6–62, warning 45–110, evacuation 101–196 mm/day. Same displacement value in different terrain zones yields different class labels.
- **Class distribution:** 61.01% safe / 26.04% warning / 12.96% evacuation (from `split_metadata.json`).
- Thresholds applied to `risk_score`, not raw displacement.
- **Result:** 75 crossover pairs. Contextual features now influence labels.
- **SHAP:** RF terrain/SAR = 18.63% (val), 17.03% (test). XGBoost = 6.75% (val), 6.90% (test).
- **This is the production dataset.**

### v2b — Isolation Test (Multiplier Alone, Original Range [0.70, 1.30])

- Tests whether the multiplier alone (without range widening) drives SHAP contribution.
- **Result:** 0 crossover pairs, XGBoost 0.00%, RF 30.31%.
- **Insight:** RF is more sensitive to structural features; XGBoost needs explicit crossover signal.

### v2c — Isolation Test (Multiplier Alone, Aggressive Range [0.50, 1.60])

- Same as v2b but with a much wider, physically aggressive multiplier range.
- **Result:** 3 crossover pairs (0.05%), XGBoost 0.00%, RF 30.31% (identical to v2b to four decimal places).
- **Insight:** Range widening alone doesn't fix XGBoost. The crossover pairs in v2 are the key.
- **RF artifact explained:** RF's 30.31% terrain/SAR SHAP is stable across v2b and v2c regardless of multiplier strength — driven by spatial autocorrelation between slope and zone tier, NOT by the label-generation mechanism itself.

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
- **Background:** Paper white `#FFFFFF` with subtle radial gradient: `radial-gradient(1200px 600px at 50% -200px, #EFF4FF 0%, #F7F9FF 35%, #FFFFFF 70%)`.
- **Typography:** Geist family (sans for body, mono for data readouts). No Inter, Outfit, or other families.
- **Layout pattern:** Row-based, not card grids. One item per horizontal line. Full-width rows with hairline dividers.

### Color Tokens

| Token | Hex | Usage |
|---|---|---|
| `ink` | `#2563EB` | Primary accent: eyebrows, focus rings, links, active dots |
| `inkDeep` | `#1D4ED8` | Hover state for ink |
| `inkSoft` | `#EFF4FF` | 10-second summary callout background |
| `paper` | `#FFFFFF` | Default surface |
| `paperWarm` | `#FBFBFD` | Alternate surface for inset cards |
| `inkDark` | `#0B1220` | Primary text: headlines, numerics, buttons |
| `muted` | `#5B6472` | Secondary text: descriptions, captions |
| `mutedSoft` | `#8A93A1` | Tertiary text: placeholders, axis labels |
| `hairline` | `#E6E8EE` | All dividers, input borders, table lines |
| `safe` | `#047857` | Safe state, success callouts |
| `warning` | `#B45309` | Warning state, amber callouts |
| `danger` | `#B91C1C` | Evacuation state, error callouts |

### Typography Scale

| Role | Family | Size | Weight | Tracking |
|---|---|---|---|---|
| Chapter eyebrow | Geist Mono | 11px | normal | 0.22em uppercase |
| Chapter title | Geist | 24→30px | 600 | -0.02em |
| Row Q-num | Geist Mono | 11px | normal | 0.18em uppercase |
| Row headline | Geist | 18→20px | 600 | -0.01em |
| Body | Geist | 15→16px | 400 | 0, leading 1.7 |
| Numeric (big) | Geist Mono | 60→84px | 600 | -0.04em |

### Anti-Patterns (do not ship)

- Dark slate backgrounds as default
- Card grids (2-up or 3-up Q&A, 4-up stat tiles)
- Glassmorphism, blur-backdrop cards, neon glows
- Purple-to-pink gradients
- Emoji as primary visual hierarchy
- Heavy borders, drop shadows on every block
- Centered hero with three identical feature cards

### Component Patterns

- **TopBar:** Sticky, `backdrop-blur-xl`, `bg-white/80`, hairline bottom border. Search-first (no H1), pill-shaped search input with `Ctrl+K` hint.
- **Tabs:** Single row, underline style, `text-[13px] font-medium`, active tab has `2px ink-blue underline`.
- **Rows:** Left column (48–64px) for mono labels, right column for content. Hairline `border-b` between rows.
- **10-second summary:** `bg-[#EFF4FF] border-l-2 border-[#2563EB]` callout inside rows.
- **Buttons:** Primary `bg-[#0B1220] text-white rounded-full`, secondary `border border-[#E6E8EE]`, accent `bg-[#2563EB]`. No scale/translate/shadow on hover.
- **Stats blocks:** Hairline grid (`gap-px bg-[#E6E8EE]`), not separate cards.
- **Modal:** Backdrop `bg-[#0B1220]/40 backdrop-blur-sm`, card `rounded-3xl p-7 shadow-2xl`.

### Accessibility

- **Contrast:** `#0B1220` on `#FFFFFF` = 18.7:1 (AAA). `#5B6472` on `#FFFFFF` = 7.0:1 (AA).
- **Focus rings:** `focus:ring-2 focus:ring-[#2563EB]/15 focus:border-[#2563EB]`.
- **Tap targets:** Minimum 44×44px (Apple HIG, WCAG 2.5.5).
- **Tab order:** Search → filter pills → timer → tabs → first row → expand.
- **`aria-hidden`** on decorative SVGs. **`aria-label`** on icon-only buttons.

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

### GET /

**Purpose:** Root endpoint — service identification and uptime.

**Response:**
```json
{
  "service": "rockfall-prediction-backend",
  "status": "online",
  "uptime_seconds": 12345.6,
  "timestamp": "2026-08-15T10:30:00Z"
}
```

---

### GET /health

**Purpose:** Liveness probe and service identification.

**Response:**
```json
{
  "status": "ok",
  "model_version": "rf-v2-20260820",
  "service": "rockfall-prediction-backend"
}
```

**Used by:** GitHub Actions heartbeat (keep-render-alive.yml) every 14 minutes.

---

### POST /predict

**Purpose:** Run a single sensor reading through the ML model and return a risk prediction.

**Also mounted at:** `/api/rockfall/predict` (dual-mount pattern in `main.py`).

**Request body:** `SensorReading` (see [Data Schemas](#15-data-schemas)).

**Response:** `RiskPrediction` (see [Data Schemas](#15-data-schemas)).

**Example:**
```json
// Request
{
  "sensor_id": "sensor-07",
  "zone_id": "zone_12",
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
  "zone_id": "zone_12",
  "timestamp": "2026-08-15T10:30:00Z",
  "risk_level": "warning",
  "risk_score": 0.73,
  "displacement_velocity_mm_day": 85.2,
  "model_version": "rf-v2-20260820"
}
```

---

### WS /ws/feed (also aliased as /ws)

**Purpose:** Real-time telemetry and alert streaming via WebSocket.

**Protocol:** `ws://` or `wss://` (upgrade from HTTP).

**Broadcast interval:** 2.5 seconds per tick (configurable via `BROADCAST_INTERVAL_SECONDS` env var).

**Message types:**

#### telemetry_update
```json
{
  "type": "telemetry_update",
  "sensor_reading": {
    "sensor_id": "sensor-03",
    "zone_id": "zone-05",
    "timestamp": "2026-08-15T10:30:00Z",
    "displacement_mm_day": 12.4,
    "vibration": 0.18,
    "pore_pressure": 205.0,
    "strain": 0.0012,
    "rainfall_mm": 3.2,
    "risk_level": null
  },
  "risk_prediction": {
    "zone_id": "zone-05",
    "timestamp": "2026-08-15T10:30:00Z",
    "risk_level": "safe",
    "risk_score": 0.12,
    "displacement_velocity_mm_day": 12.4,
    "model_version": "rf-v2-20260820"
  },
  "timestamp": "2026-08-15T10:30:00Z"
}
```

#### alert_event
```json
{
  "type": "alert_event",
  "payload": {
    "alert_id": "ALT-zone_12-20260815T103000123456",
    "zone_id": "zone_12",
    "severity": "evacuation",
    "message": "Risk escalated to EVACUATION in zone_12. Immediate action required.",
    "triggered_at": "2026-08-15T10:30:00Z",
    "acknowledged": false
  },
  "timestamp": "2026-08-15T10:30:00Z"
}
```

**Alert trigger logic:** An `alert_event` is emitted when a zone's risk class crosses upward (Safe→Warning, Warning→Evacuation, or Safe→Evacuation). Duplicate alerts for the same zone + severity within a cooldown window are suppressed.

---

## 15. Data Schemas

### SensorReading

```typescript
interface SensorReading {
  sensor_id: string;          // e.g. "sensor-07"
  zone_id: string;            // e.g. "zone_12"
  timestamp: string;          // ISO 8601
  displacement_mm_day: number; // Daily displacement in mm
  vibration: number;          // Normalised vibration index
  pore_pressure: number;      // kPa
  strain: number;             // Microstrain
  rainfall_mm: number;        // Daily rainfall in mm
  risk_level?: string | null; // Optional override (usually null, model predicts)
}
```

**Pydantic enforcement:** `risk_score` field uses `Field(..., ge=0.0, le=1.0)` — constrained to [0, 1] at validation time.

**Threshold constants** (defined as module-level constants in `backend/app/schemas.py` and mirrored in `frontend/lib/types.ts`):
- `SAFE_DISPLACEMENT_MAX_MM_DAY = 50.0`
- `WARNING_DISPLACEMENT_MAX_MM_DAY = 120.0`

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
  alert_id: string;                   // e.g. "ALT-zone_01-20260815T103000123456"
  zone_id: string;
  severity: "safe" | "advisory" | "warning" | "evacuation";
  message: string;                    // Human-readable
  triggered_at: string;               // ISO 8601
  acknowledged: boolean;              // Default false
}
```

- `"warning"` / `"evacuation"`: emitted on upward class crossings (Safe→Warning, Warning→Evacuation).
- `"advisory"`: emitted on **downgrade** transitions (Evacuation→Warning, Warning→Safe).
- `"safe"`: used in TypeScript frontend type but not currently emitted by backend.

### WebSocket Message Envelope Types

```typescript
interface TelemetryUpdateMessage {
  type: "telemetry_update";
  sensor_reading: SensorReading;
  risk_prediction: RiskPrediction;
  timestamp: string;
}

interface AlertEventMessage {
  type: "alert_event";
  payload: AlertEvent;
  timestamp: string;
}

type WebSocketMessage = TelemetryUpdateMessage | AlertEventMessage;
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
- **Service name:** `sih25071-rockfall-backend`.
- **Runtime:** Python 3.12, uvicorn.
- **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- **Auto-deploy:** Enabled (`autoDeploy: true` in `render.yaml`).
- **Environment variables:** `PYTHON_VERSION=3.12.0` (in yaml), `FRONTEND_ORIGIN` (set in Render dashboard, sync: false).
- **Sleep behaviour:** After 15 minutes of inactivity.
- **Cold start:** ~30–60 seconds (loads RF model into memory).
- **Mitigation:** GitHub Actions cron pings `GET /health` every 14 minutes.
- **Config:** `render.yaml` + `runtime.txt`.

### Frontend (Vercel)

- **Platform:** Vercel (hobby tier).
- **Framework:** Next.js 16.3.1 with Turbopack (`next dev --turbopack`), optimised for Vercel.
- **Deploy trigger:** Push to main branch (auto-deploy).
- **Environment variables:**
  - `NEXT_PUBLIC_API_URL=https://sih2026-xk4z.onrender.com`
  - `NEXT_PUBLIC_WS_URL=wss://sih2026-xk4z.onrender.com/ws/feed`
- **Metadata title:** "SIH 2026 • AI Rockfall Early Warning System"

### Heartbeat

**File:** `.github/workflows/keep-render-alive.yml`

```yaml
on:
  schedule:
    - cron: '*/14 * * * *'  # Every 14 minutes (under Render's 15-min idle threshold)
  workflow_dispatch:          # Manual trigger for demo-day warm-up
jobs:
  keep-alive:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Ping backend health endpoint
        run: |
          HTTP_STATUS=$(curl -s -o response.txt -w "%{http_code}" --max-time 60 \
            https://sih2026-xk4z.onrender.com/health)
          if [ "$HTTP_STATUS" -ne 200 ]; then
            echo "ERROR: Health check returned HTTP $HTTP_STATUS"
            cat response.txt
            exit 1
          fi
          echo "OK: HTTP $HTTP_STATUS"
          cat response.txt
```

- **`workflow_dispatch`**: allows manual warm-up trigger before demo presentation.
- **Error handling**: captures HTTP status + body, fails loudly on non-200.
- **Curl timeout**: 60 seconds (`--max-time 60`).

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

1. Convert RF v2 model to ONNX (`skl2onnx` — works directly via `to_onnx()`).
2. Convert XGBoost to ONNX (**requires `onnxmltools` + `update_registered_converter`** — `skl2onnx` alone does not handle XGBoost).
3. Convert GRU to ONNX (`torch.onnx.export`).
4. Write a Python inference script that reads sensor data, runs ONNX, outputs alerts.
5. Deploy to Raspberry Pi with a cellular/WiFi link for local SMS/buzzer alerts.

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

**Rebuttal:** On this class distribution, a model that always predicts "safe" scores roughly 60% accuracy and is worthless — it never once catches a real evacuation event. That's exactly why we don't report accuracy as our headline metric. We report precision and recall on the evacuation class specifically, using class-weighted training so the loss function itself penalises missing a rare evacuation event far more than misclassifying a safe reading. A missed evacuation is a life-safety failure; a false alarm is an inconvenience — our metric choice reflects that asymmetry.

#### "You're using synthetic data."

**Rebuttal:** Yes, and we're honest about it. The synthetic data is generated using the Fukuzono (1985) inverse velocity model — the same physics used in real SSR systems. The terrain, SAR, and rainfall data are real (Copernicus, Sentinel-1, Open-Meteo). The synthetic component is the sensor stream, which would be replaced by real IoT sensors in production. The choice to use synthetic data is defensible because:
1. Real mine sensor datasets are proprietary and unavailable for hackathons.
2. Physics-informed synthesis ensures realistic displacement acceleration patterns.
3. The ML pipeline is agnostic to data source — swapping in real sensors requires zero model changes.

#### "Why not InSAR? SAR backscatter is low resolution."

**Rebuttal:** We use Sentinel-1 GRD **amplitude backscatter**, not InSAR (interferometric phase). InSAR requires precise co-registration, atmospheric correction, and has decorrelation issues in vegetated or steep terrain. Backscatter is more robust as a contextual feature — it correlates with surface roughness, moisture, and disturbance. It's a proxy, not a displacement measurement, and the model uses it as one feature among many.

#### "Why class weighting over SMOTE?"

**Rebuttal:** SMOTE synthesises new samples by interpolating between existing minority-class neighbours. In our dataset, features are physically correlated — displacement autocorrelates over time, rainfall has seasonality, SAR backscatter changes slowly. SMOTE would create physically impossible feature combinations (e.g., high displacement with low rainfall and anomalous SAR in a way that can't occur in reality). Class weighting preserves every real sample's physical integrity.

**One-liner (memorise):** *"We use class-weighted loss rather than SMOTE because our sensor channels are physically correlated by construction — synthetic interpolation risks generating physically implausible readings. Weighting keeps every training point real."*

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
