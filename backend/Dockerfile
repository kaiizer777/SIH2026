# ── Backend Dockerfile ────────────────────────────────────────────────────────
# python:3.12-slim keeps the image lean; uvicorn serves the FastAPI app.
# models/ and data/ are mounted via docker-compose volume — not baked in —
# so the image stays small and artifacts don't need rebuilding on model updates.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Prevents Python from writing .pyc files and buffers stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps (needed by scikit-learn / numpy wheel builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps first (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source (models/ and data/ come in via bind-mount, not here)
COPY . .

EXPOSE 8001

# Run with uvicorn; reload disabled in prod.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
