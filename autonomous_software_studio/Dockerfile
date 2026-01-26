# =============================================================================
# Autonomous Software Studio - Orchestrator Service
# Production-ready multi-stage Docker build
# =============================================================================

FROM python:3.11-slim AS base

# Prevent Python from writing bytecode and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies including PostgreSQL client libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    bash \
    ca-certificates \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd -m -s /bin/bash -u 1000 appuser

# =============================================================================
# Builder stage - install Python dependencies
# =============================================================================
FROM base AS builder

COPY requirements.txt .

# Install dependencies to a separate prefix for clean copy
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# =============================================================================
# Runtime stage - final production image
# =============================================================================
FROM base AS runtime

# Install claude-code CLI for the appuser
RUN su - appuser -c "curl -fsSL https://claude.ai/install.sh | bash" || true
RUN su - appuser -c "test -x /home/appuser/.local/bin/claude || test -x /home/appuser/.local/bin/claude-code || echo 'Claude CLI optional'"

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser docs/ ./docs/

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/reports /app/projects \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PATH="/home/appuser/.local/bin:${PATH}" \
    PYTHONPATH=/app \
    # Application defaults
    LOG_LEVEL=INFO \
    DEBUG_MODE=false \
    # Database configuration (can be overridden)
    DATABASE_TYPE=postgresql \
    # Streamlit settings
    STREAMLIT_SERVER_SHOW_EMAIL_PROMPT=false \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Expose orchestrator API port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default command - run orchestrator server
CMD ["python", "-m", "src.orchestration.orchestrator", "--server", "--host", "0.0.0.0", "--port", "8000"]
