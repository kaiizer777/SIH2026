# SIH25071 — AI-Based Rockfall Prediction and Alert System for Open-Pit Mines

> A comprehensive real-time geotechnical surveillance and early-warning platform for open-pit mines utilizing AI predictive models, telemetry analytics, and spatial risk heatmaps.

---

## 📁 Repository Structure

```
SIH2026/
├── frontend/                 # Next.js 16 (App Router + Turbopack + Tailwind CSS)
│   ├── app/
│   │   ├── dashboard/        # Open-pit map & risk heatmap view
│   │   ├── alerts/           # Alert log & incident dispatch UI
│   │   ├── trends/           # Time-series sensor telemetry charts
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── map/              # MapLibre GL 3D pit heatmap components
│   │   └── charts/           # Recharts time-series telemetry charts
│   ├── lib/
│   │   ├── api.ts            # Typed fetch client for FastAPI backend
│   │   └── websocket.ts      # WebSocket client for real-time sensor streams
│   ├── types/
│   │   └── index.ts          # Shared TypeScript domain interfaces
│   ├── .env.local.example
│   └── package.json
│
├── backend/                  # FastAPI 0.141 microservice (Python 3.12)
│   ├── main.py               # FastAPI app instance, CORS middleware, health checks
│   ├── routers/              # API route modules (inference, alerts, sensors)
│   ├── models/               # Pydantic schemas & data models
│   ├── requirements.txt      # Python dependencies
│   └── .env.example
│
├── .gitignore                # Unified root gitignore
└── README.md
```

---

## 🚀 Quick Start

### 1. Frontend (Next.js)

```bash
cd frontend

# Copy environment variables
cp .env.local.example .env.local

# Install dependencies (if not already installed)
npm install

# Start development server with Turbopack
npm run dev
```

Frontend will run at `http://localhost:3000`.

---

### 2. Backend (FastAPI)

```bash
cd backend

# Create & activate virtual environment (Windows PowerShell)
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1

# (Linux / macOS)
# python3.12 -m venv venv
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Run FastAPI dev server
uvicorn main:app --reload --port 8000
```

Backend will run at `http://localhost:8000`.  
Interactive API docs: `http://localhost:8000/docs`.
