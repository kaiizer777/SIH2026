import asyncio
from contextlib import asynccontextmanager
import os
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

try:
    from backend.routers.rockfall import (
        broadcast_sensor_feed_loop,
        manager,
        router as rockfall_router,
    )
except ImportError:
    from routers.rockfall import (
        broadcast_sensor_feed_loop,
        manager,
        router as rockfall_router,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background sensor & prediction telemetry broadcaster
    broadcast_task = asyncio.create_task(broadcast_sensor_feed_loop(interval_seconds=2.5))
    yield
    # Graceful shutdown of background task
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass


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

# Include Rockfall routes at root (POST /predict, WS /ws/feed) and /api/rockfall prefix
app.include_router(rockfall_router)
app.include_router(rockfall_router, prefix="/api/rockfall")


# WebSocket alias for /ws
@app.websocket("/ws")
async def websocket_alias(websocket: WebSocket):
    from backend.routers.rockfall import websocket_feed
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
    return {
        "status": "healthy",
        "service": "rockfall-prediction-backend",
        "version": "1.0.0",
    }
