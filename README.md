# SIH25071 — AI-Based Rockfall Prediction & Alert System

[![Ministry of Mines](https://img.shields.io/badge/SIH25071-Ministry%20of%20Mines-orange?style=flat-square)](https://www.sih.gov.in/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.141-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016-000000?style=flat-square&logo=nextdotjs)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Docker Backend](https://img.shields.io/docker/v/kaizer777/sih2026-backend?label=Docker%20Backend&logo=docker&style=flat-square)](https://hub.docker.com/r/kaizer777/sih2026-backend)
[![Docker Frontend](https://img.shields.io/docker/v/kaizer777/sih2026-frontend?label=Docker%20Frontend&logo=docker&style=flat-square)](https://hub.docker.com/r/kaizer777/sih2026-frontend)

An end-to-end geotechnical surveillance and early-warning platform designed for open-pit mines. The system fuses multi-modal environmental, spatial, and sensor telemetry into physics-grounded machine learning models to forecast slope instability and trigger sub-minute evacuation alerts.

**Live:** [Backend](https://sih2026-xk4z.onrender.com) · [Frontend](https://sih-2026-drab.vercel.app) · [API Docs](https://sih2026-xk4z.onrender.com/docs)

## About The Project

**SIH25071** is an AI/ML-powered geotechnical early-warning and slope stability surveillance platform tailored for open-pit / opencast mining operations (aligned with the **Ministry of Mines, Disaster Management** theme).

In opencast mines (such as SECL Kusmunda, Korba Coalfield, Chhattisgarh), slope failure and bench rockfalls represent critical occupational hazards. While industrial **Slope Stability Radar (SSR)** systems deliver sub-millimeter displacement tracking, their high capital expenditure (~$250k–$500k/unit) and line-of-sight constraints leave peripheral and smaller-scale pits unmonitored.

This platform bridges that gap by fusing **distributed geotechnical sensor telemetry**, **satellite Earth observation**, and **meteorological data** into a unified, physics-grounded machine learning pipeline:

* **Multi-Modal Remote Sensing & Meteorology:** Copernicus GLO-30 DEM for slope/aspect/curvature via Google Earth Engine; Sentinel-1 SAR (C-band GRD) backscatter change detection as a surface-disturbance proxy; Open-Meteo ERA5 precipitation data.
* **Physics-Informed Geotechnical Telemetry:** Displacement, pore pressure, vibration, and strain calibrated under the **Fukuzono (1985) Inverse Velocity Method** — displacement accelerates and inverse velocity trends to zero before failure.
* **Imbalance-Aware ML Engine:** Class-weighted loss (not SMOTE — physically-correlated channels risk implausible synthetic interpolation). Models: RandomForest, XGBoost (production champion — 100% evacuation recall), GRU (benchmark). Exportable to **ONNX Runtime** for offline edge alerting.
* **Real-Time 3D Dashboard:** Next.js 16 + MapLibre GL pit heatmaps, WebSocket telemetry charts, and evacuation dispatch logs.

---

## Problem & Physical Grounding

* **Problem Statement:** SIH25071 | Ministry of Mines (Disaster Management Theme)
* **Goal:** Mitigate fatal slope failures in opencast mines where SSR coverage is unavailable.
* **Physical Basis:**
  * **Inverse Velocity Method (Fukuzono, 1985):** Displacement rate accelerates before failure; inverse velocity trends to zero — enables lead-time forecasting.
  * **Empirical Risk Thresholds** (Indonesian open-pit coal SSR case study):
    * **Safe:** 0–50 mm/day
    * **Warning:** 50–120 mm/day
    * **Evacuation:** >120 mm/day

---

## System Architecture

```
[Geotechnical Sensors + Sentinel-1 SAR + GLO-30 DEM + Open-Meteo API]
                               │
                               ▼
                  [FastAPI Stream & Ingestion]
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
     [ML Inference Engine]           [Edge Node (ONNX)]
 (RF/XGBoost + GRU TimeSeries)    (Local Siren / Offline Mode)
               │                               │
               └───────────────┬───────────────┘
                               ▼
                   [Real-Time WebSocket Feed]
                               ▼
           [Next.js 16 Dashboard (MapLibre + Recharts)]
```

---

## Model Performance (Test Set — Evacuation Class)

| Metric | RandomForest (v2) | XGBoost (v2) | GRU |
|:---|:---|:---|:---|
| **Precision** | 0.9949 | 0.9704 | 1.0000 |
| **Recall** | 0.9848 | 1.0000 | 0.7208 |
| **F1-Score** | 0.9898 | 0.9850 | 0.8378 |
| **Missed Evacuations** | 3 / 197 | 0 / 197 | 55 / 197 |

XGBoost is the production champion (zero missed evacuations). RF ships on the live backend for its stronger terrain/SAR SHAP signal (17.03% vs 6.90%). GRU is benchmarked for architectural completeness — all 55 misses land in Warning, not Safe.

---

## Tech Stack

| Layer | Technologies |
|:---|:---|
| **Frontend** | Next.js 16.3 (App Router, Turbopack), React 19, TypeScript 5.9, Tailwind CSS 4 |
| **Mapping & Viz** | MapLibre GL + React-Map-GL (open-source 3D terrain), Recharts |
| **Backend API** | FastAPI 0.141, Python 3.12, Uvicorn, WebSockets |
| **ML & Inference** | Scikit-learn, XGBoost, PyTorch (GRU), ONNX Runtime, SHAP |
| **Deployment** | Vercel (Frontend) + Render (Backend) |
| **Containerisation** | Docker + Docker Compose · Images on [Docker Hub (`kaizer777`)](https://hub.docker.com/u/kaizer777) |

---

## Repository Structure

```
SIH2026/
├── frontend/             # Next.js 16 App Router UI
│   ├── app/              # Routes: /dashboard, /alerts, /trends, /pitch
│   ├── components/       # MapLibre 3D heatmap, Recharts trends, TopBar
│   └── lib/              # API client, WebSocket client, TypeScript types
│
├── backend/              # FastAPI microservice
│   ├── main.py           # Entrypoint, lifespan, CORS, router mount
│   ├── app/schemas.py    # Pydantic: SensorReading, RiskPrediction, AlertEvent
│   ├── app/physics_generator.py  # Fukuzono-based live sensor generator
│   └── routers/rockfall.py       # POST /predict, WS /ws/feed, alert logic
│
├── models/               # Trained artifacts (RF, XGBoost, GRU + metadata)
├── data/                 # DEM, SAR, rainfall, synthetic sensors, sequences
├── scripts/              # Phase scripts (terrain → training → integration)
├── tests/                # Pytest: endpoint, WebSocket, alert dedup, physics
├── reports/              # SHAP plots, confusion matrices
├── docs/                 # CONTEXT.md, WORKFLOW.md, session logs, pitch drafts
└── frontend.md           # Frontend design guide (single source of truth)
```

---

## Quick Start

### 🐳 Docker (recommended — zero setup)

```bash
# 1. Copy and fill in env vars (add your GROQ_API_KEY)
cp .env.docker.example .env.docker

# 2. Build and start both services
docker compose up --build
```

| Service | URL |
|:---|:---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8001 |
| API Docs | http://localhost:8001/docs |

Or pull pre-built images directly:

```bash
docker pull kaizer777/sih2026-backend:latest
docker pull kaizer777/sih2026-frontend:latest
```

> **Note:** `models/` and `data/` are mounted from the repo root at runtime — clone the full repo before running.

---

### Manual Setup

#### 1. Backend (FastAPI)

```bash
cd backend

# Create & activate Python 3.12 venv
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1   # Windows PowerShell
# source venv/bin/activate     # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload --port 8000
```
> API Docs at `http://localhost:8000/docs`

#### 2. Frontend (Next.js)

```bash
cd frontend

# Install packages
npm install

# Start development server
npm run dev
```
> Dashboard at `http://localhost:3000`

---

## Documentation

| Doc | Description |
|:---|:---|
| [`docs/CONTEXT.md`](docs/CONTEXT.md) | Full engineering spec, scientific references, all 29 phases, API reference, glossary |
| [`docs/WORKFLOW.md`](docs/WORKFLOW.md) | Day 0 → Demo execution plan |
| [`frontend.md`](frontend.md) | Frontend design guide (colors, typography, components, responsiveness) |
| [`AGENTS.md`](AGENTS.md) | AI agent operational directives |
