import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

app = FastAPI(
    title="SIH25071 - Rockfall Prediction & Alert API",
    description="Backend microservice for open-pit slope stability analysis, AI rockfall prediction, and alert telemetry.",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from backend.routers.rockfall import router as rockfall_router
except ImportError:
    from routers.rockfall import router as rockfall_router

START_TIME = time.time()

app.include_router(rockfall_router)




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
