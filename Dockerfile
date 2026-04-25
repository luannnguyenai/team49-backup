# syntax=docker/dockerfile:1.7

# Use a lightweight Python base image
FROM python:3.12-slim-bookworm AS runtime

# Install system dependencies and uv
# uv is a fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project configuration files
COPY pyproject.toml uv.lock* ./

# Install dependencies only and persist uv's download/build cache across builds.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application code
COPY . .

# Add /app to PYTHONPATH so src.api.app etc. work
ENV PYTHONPATH="/app"

# Expose the API port
EXPOSE 8000

# Default production-safe startup for the standalone backend image.
# Compose can still override this for dev reload or multi-worker prod.
CMD ["uv", "run", "python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
