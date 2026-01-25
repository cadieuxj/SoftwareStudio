FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser

FROM base AS builder

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM base AS runtime

# Install claude-code CLI (installer requires bash)
RUN su - appuser -c "curl -fsSL https://claude.ai/install.sh | bash"
RUN su - appuser -c "command -v claude || command -v claude-code || test -x /home/appuser/.local/bin/claude || test -x /home/appuser/.local/bin/claude-code"

COPY --from=builder /install /usr/local
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY docs/ ./docs/

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/docs /app/reports /app/projects \
    && chown -R appuser:appuser /app

USER appuser

ENV PATH="/home/appuser/.local/bin:${PATH}" \
    PYTHONPATH=/app \
    STREAMLIT_SERVER_SHOW_EMAIL_PROMPT=false \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["python", "-m", "src.orchestration.orchestrator", "--server", "--host", "0.0.0.0", "--port", "8000"]
