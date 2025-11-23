# Multi-stage Dockerfile for production-ready Python application
# Base image: Python 3.11 on Debian Bookworm (slim)

# ============================================
# Build Arguments
# ============================================
ARG PYTHON_VERSION=3.11

# ============================================
# Stage 1: Base Python Image
# ============================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# Metadata
LABEL maintainer="SecureTempMail"
LABEL description="Production-ready temporary email system"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONHASHSEED=random \
    PYTHONIOENCODING=utf-8

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ============================================
# Stage 2: Dependencies Builder
# ============================================
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ============================================
# Stage 3: Production Image
# ============================================
FROM base AS production

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user and group
RUN groupadd -r -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -m -s /bin/bash appuser && \
    mkdir -p /app /app/logs && \
    chown -R appuser:appuser /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Set PATH to use virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser ./app ./app
COPY --chown=appuser:appuser ./scripts ./scripts

# Ensure scripts are executable
RUN chmod +x ./scripts/*.sh 2>/dev/null || true

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app/logs /app/data

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 8000 8025 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-config", "app/core/logging_config.json"]

# ============================================
# Stage 4: Development Image
# ============================================
FROM base AS development

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    git \
    vim \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt requirements-dev.txt ./

# Install all dependencies (including dev)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Expose ports
EXPOSE 8000 8025 9090

# Development command with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]