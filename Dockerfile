# =============================================================================
# Dockerfile — FastAPI backend (Python 3.11, multi-stage)
# =============================================================================

# ── Stage 1: builder — install deps into /install ────────────────────────────
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /build

# Build deps for asyncpg / psycopg2-binary / cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --target=/install -r requirements.txt


# ── Stage 2: runtime — minimal image ─────────────────────────────────────────
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:/app/deps" \
    PORT=8000

WORKDIR /app

# Runtime-only system libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /app/deps

# Copy application source (excluding dev/test artefacts via .dockerignore)
COPY . .

# Non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production: uvicorn with 4 workers.
# Override CMD in docker-compose.yml for dev (--reload).
CMD ["python", "-m", "uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
