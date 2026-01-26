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

# Install system dependencies including PostgreSQL client libraries and Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    bash \
    ca-certificates \
    libpq-dev \
    gcc \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
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

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Install Claude Code CLI globally via npm
RUN npm install -g @anthropic-ai/claude-code || true

# Install Claude CLI for the appuser (alternative installation method)
USER appuser
RUN mkdir -p /home/appuser/.local/bin \
    && curl -fsSL https://claude.ai/install.sh | bash 2>/dev/null || true \
    && curl -fsSL https://www.anthropic.com/claude-code/install.sh | bash 2>/dev/null || true

# Verify installation (don't fail if not installed)
RUN which claude || which claude-code || echo "Claude CLI will be configured at runtime"

USER root

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
ENV PATH="/home/appuser/.local/bin:/usr/local/bin:${PATH}" \
    PYTHONPATH=/app \
    NODE_PATH=/usr/lib/node_modules \
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
