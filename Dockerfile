# Build stage
FROM python:3.15-slim@sha256:ea4f1f290e071bf7d28199cfb3e09f5dbad31b50e9c32fd58f2f2d7be915f3ae AS builder

WORKDIR /build

# Install system dependencies needed for building (minimal set)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv for dependency management
RUN pip install --no-cache-dir uv==0.7.15

# Copy dependency files first for better caching
COPY pyproject.toml .python-version ./

# Install Python dependencies using uv (production only)
RUN uv sync --no-dev

# Production stage
FROM python:3.15-slim@sha256:ea4f1f290e071bf7d28199cfb3e09f5dbad31b50e9c32fd58f2f2d7be915f3ae

WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv in production stage (pin version for reproducibility)
RUN pip install --no-cache-dir uv==0.7.15

# Copy Python virtual environment from builder stage
COPY --from=builder /build/.venv /app/.venv

# Copy dependency files
COPY pyproject.toml .python-version ./

# Copy application code
COPY app.py ./
COPY lib/ ./lib/
COPY templates/ ./templates/

# Create directories for storage and logs
RUN mkdir -p /app/stored_configs /app/logs

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app
USER app

# Create volume for persistent storage
VOLUME ["/app/stored_configs", "/app/logs"]

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application with gunicorn for production
CMD ["/app/.venv/bin/python", "-m", "gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "60", \
     "--worker-class", "sync", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--preload", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]