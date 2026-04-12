# Use a lightweight Python base image
FROM python:3.12-slim-bookworm AS runtime

# Install system dependencies and uv
# uv is a fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project configuration files
COPY pyproject.toml uv.lock* ./

# Install dependencies only (cached if pyproject.toml doesn't change)
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application code
COPY . .

# Add /app to PYTHONPATH so src.api.app etc. work
ENV PYTHONPATH="/app"

# Expose the API port
EXPOSE 8000
# Expose Streamlit port
EXPOSE 8501

# Command to run the FastAPI backend
# We use 'uv run' to ensure the environment is correctly set up
CMD ["uv", "run", "python", "src/api/app.py"]
