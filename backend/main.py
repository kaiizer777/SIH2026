import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

# ---------------------------------------------------------------------------
# Resolve paths relative to repo root (one level above backend/)
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _BACKEND_DIR.parent

MODEL_PATH         = _REPO_ROOT / "models" / "rf-v2-20260820.joblib"
FEATURE_ORDER_PATH = _REPO_ROOT / "models" / "feature_order.json"
LABEL_ENCODING_PATH = _REPO_ROOT / "models" / "label_encoding.json"
ZONE_FEATURES_PATH  = _REPO_ROOT / "data" / "zone_features.csv"

MODEL_VERSION = "rf-v2-20260820"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # -----------------------------------------------------------------------
    # FAIL-FAST startup -- any missing artifact crashes the worker intentionally.
    # Do NOT wrap in try/except. A worker that can't load its model must not
    # serve requests. Render's process manager will flag the crash; a silent
    # start that 500s on first request is worse.
    # -----------------------------------------------------------------------
    app.state.model = joblib.load(MODEL_PATH)
    app.state.feature_order = json.loads(FEATURE_ORDER_PATH.read_text(encoding="utf-8"))
    app.state.label_encoding = json.loads(LABEL_ENCODING_PATH.read_text(encoding="utf-8"))

    # zone_features loaded once into memory -- static terrain/SAR lookup table.
    # Holds 480 rows (16 zones x 30 SAR acquisition dates).
    zf = pd.read_csv(ZONE_FEATURES_PATH)
    zf["_zf_date"] = pd.to_datetime(zf["date"])
    zf = zf.sort_values(["zone_id", "_zf_date"]).reset_index(drop=True)
    app.state.zone_features = zf

    app.state.model_version = MODEL_VERSION

    # -----------------------------------------------------------------------
    # Phase 21: Physics-informed generator state -- initialized ONCE at startup.
    # All 16 zones get persistent ZoneGeneratorState instances stored on app.state.
    # Each zone's state is stepped forward by one tick per broadcast cycle.
    # Re-creating state per tick would produce independent random readings with no
    # temporal continuity -- exactly what Phase 21 exists to prevent.
    # -----------------------------------------------------------------------
    try:
        from backend.app.physics_generator import load_generator_data, initialize_all_zone_states
    except ImportError:
        from app.physics_generator import load_generator_data, initialize_all_zone_states  # type: ignore

    api_norm, rainfall_values, sim_dates, zone_risk_map, zone_multipliers = load_generator_data(
        repo_root=_REPO_ROOT,
    )
    app.state.api_norm = api_norm
    app.state.rainfall_values = rainfall_values
    app.state.sim_dates = sim_dates

    app.state.zone_generator_state = initialize_all_zone_states(zone_risk_map, zone_multipliers)
    logger.info(
        "Physics generator initialized: %d zones, api_norm shape %s, dates %s..%s",
        len(app.state.zone_generator_state),
        api_norm.shape,
        sim_dates[0],
        sim_dates[-1],
    )

    # Per-zone last-known risk level for alert de-duplication.
    # Initialized to None so the first reading that crosses into warning/evacuation
    # fires exactly one alert, per the Phase 21 crossing-INTO semantics.
    app.state.zone_last_risk_level: dict[str, str | None] = {
        zone_id: None for zone_id in app.state.zone_generator_state
    }

    # Round-robin cursor for zone tick rotation (advances 0..15 cycling)
    app.state.zone_tick_cursor: int = 0

    # Import here to avoid circular-import at module load time
    try:
        from backend.routers.rockfall import broadcast_sensor_feed_loop, manager
    except ImportError:
        from routers.rockfall import broadcast_sensor_feed_loop, manager  # type: ignore

    broadcast_task = asyncio.create_task(broadcast_sensor_feed_loop(app, interval_seconds=2.5))
    logger.info("Broadcast task started (interval=2.5s, 16 zones round-robin)")

    yield

    # Graceful shutdown
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass

    del app.state.model


app = FastAPI(
    title="SIH25071 - Rockfall Prediction & Alert API",
    description="Backend microservice for open-pit slope stability analysis, AI rockfall prediction, and alert telemetry.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()

# Include Rockfall routes
try:
    from backend.routers.rockfall import router as rockfall_router, websocket_feed
except ImportError:
    from routers.rockfall import router as rockfall_router, websocket_feed  # type: ignore

app.include_router(rockfall_router)
app.include_router(rockfall_router, prefix="/api/rockfall")


# WebSocket alias for /ws
@app.websocket("/ws")
async def websocket_alias(websocket: WebSocket):
    await websocket_feed(websocket)


@app.get("/")
async def root():
    return {
        "service": "SIH25071 AI Rockfall Prediction & Alert System",
        "status": "online",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.get("/health")
async def health_check():
    """Lightweight liveness probe — used by Render deploy checks and Phase 24 integration tests."""
    return {
        "status": "ok",
        "model_version": MODEL_VERSION,
        "service": "rockfall-prediction-backend",
    }
