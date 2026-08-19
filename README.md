# SIH25071 — AI-Based Rockfall Prediction & Alert System

[![Ministry of Mines](https://img.shields.io/badge/SIH25071-Ministry%20of%20Mines-orange?style=flat-square)](https://www.sih.gov.in/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.141-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016-000000?style=flat-square&logo=nextdotjs)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

An end-to-end geotechnical surveillance and early-warning platform designed for open-pit mines. The system fuses multi-modal environmental, spatial, and sensor telemetry into physics-grounded machine learning models to forecast slope instability and trigger sub-minute evacuation alerts.

## 📖 About The Project

**SIH25071** is an AI/ML-powered geotechnical early-warning and slope stability surveillance platform tailored for open-pit / opencast mining operations (aligned with the **Ministry of Mines, Disaster Management** theme).

In opencast mines (such as SECL Kusmunda, Korba Coalfield, Chhattisgarh), slope failure and bench rockfalls represent critical occupational hazards. While industrial **Slope Stability Radar (SSR)** systems deliver sub-millimeter displacement tracking, their high capital expenditure (~$250k–$500k/unit) and line-of-sight constraints leave peripheral and smaller-scale pits unmonitored. 

This platform bridges that gap by fusing **distributed geotechnical sensor telemetry**, **satellite Earth observation**, and **meteorological data** into a unified, physics-grounded machine learning pipeline:

* **🛰️ Multi-Modal Remote Sensing & Meteorology:** Extracts Copernicus GLO-30 Digital Elevation Models (DEM) for slope, aspect, and curvature profiling via Google Earth Engine (GEE); integrates Sentinel-1 SAR (C-band GRD) multi-temporal backscatter anomaly tracking ($\Delta\text{dB}$ surface disturbance proxy); streams Open-Meteo ERA5-calibrated precipitation data.
* **⚡ Physics-Informed Geotechnical Telemetry:** Real-time surface displacement, pore water pressure, micro-seismic vibration, and strain gauges calibrated under the **Fukuzono (1985) Inverse Velocity Method** ($v \to \infty, 1/v \to 0$ precursor dynamics).
* **🧠 Imbalance-Aware ML Engine:** Rigorously addresses heavy class imbalance (SMOTE / cost-sensitive loss), prioritizing minority-class precision, recall, and PR-AUC over raw accuracy. Models transition from Tree baselines (RandomForest / XGBoost) to Sequential Deep Learning (GRU) and compile to **ONNX Runtime** for zero-latency, offline edge alerting at the pit.
* **📊 Mission-Critical 3D GIS Dashboard:** Next.js 16 (React 19 + TypeScript + MapLibre GL) single-pane interface delivering 3D pit heatmaps, real-time WebSocket telemetry charts, and sub-minute evacuation dispatch logs.

---

## 📌 Problem & Physical Grounding

* **Problem Statement:** SIH25071 | Ministry of Mines (Disaster Management Theme)
* **Goal:** Mitigate fatal slope failures in opencast mines where high-cost Slope Stability Radar (SSR ~$250k–$500k/unit) coverage is unavailable or line-of-sight constrained.
* **Physical Basis:** 
  * **Inverse Velocity Method (Fukuzono, 1985):** As failure nears, displacement rate accelerates ($v \to \infty$) and inverse velocity linearly trends to zero ($1/v \to 0$), enabling calculated lead-time forecasting.
  * **Empirical Risk Thresholds:**
    * 🟢 **Safe:** $0 - 50\text{ mm/day}$
    * 🟡 **Warning:** $50 - 120\text{ mm/day}$
    * 🔴 **Evacuation:** $> 120\text{ mm/day}$

---

## 🏗️ System Architecture

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

* **Data Fusion:** Physics-informed synthetic sensor streams (displacement, pore pressure, micro-seismic, strain) calibrated against real-world datasets (Landslide4Sense, NASA GLC, Dorren et al., GSI/DGMS), fused with real DEM (Copernicus GLO-30), Sentinel-1 SAR backscatter change detection, and rainfall telemetry.
* **ML Pipeline:** Focuses heavily on **class imbalance** (SMOTE / cost-sensitive weighting) evaluating PR-AUC & minority F1-score. Models exportable to **ONNX Runtime** for local offline edge execution on low-power hardware.

---

## 🛠️ Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | Next.js 16.3 (App Router, Turbopack), React 19, TypeScript 5.9, Tailwind CSS 4 |
| **Mapping & Viz** | MapLibre GL + React-Map-GL (open-source 3D terrain), Recharts |
| **Backend API** | FastAPI 0.141, Python 3.12, Uvicorn, WebSockets |
| **ML & Inference** | Scikit-learn, XGBoost, PyTorch (GRU), ONNX Runtime, SHAP |
| **Deployment** | Vercel (Frontend) + Render (Backend) |

---

## 📁 Repository Structure

```
SIH2026/
├── frontend/             # Next.js 16 App Router UI
│   ├── app/              # Routes: /dashboard (Map), /trends (Charts), /alerts
│   ├── components/       # MapLibre 3D heatmaps & Recharts telemetry widgets
│   ├── lib/              # API and WebSocket client adapters
│   └── types/            # TypeScript schemas
│
├── backend/              # FastAPI microservice
│   ├── main.py           # Application entrypoint & health endpoints
│   ├── routers/          # API routes (rockfall inference, alerts, telemetry)
│   ├── models/           # Pydantic schemas & ML inference pipeline
│   └── requirements.txt  # Python dependencies
│
├── CONTEXT.MD            # Engineering specification & scientific references
└── README.md
```

---

## 🚀 Quick Start

### 1. Backend (FastAPI)

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
> API Docs accessible at `http://localhost:8000/docs`

### 2. Frontend (Next.js)

```bash
cd frontend

# Install packages
npm install

# Start development server
npm run dev
```
> Dashboard runs at `http://localhost:3000`
