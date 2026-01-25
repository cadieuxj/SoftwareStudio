# Deployment Guide

## Docker Compose (Recommended)
```bash
docker-compose build
docker-compose up -d
docker-compose ps
```

Note: The compose file mounts `./data`, `./logs`, `./docs`, `./reports`, and
`./projects` into both services so the dashboard can display orchestrator
artifacts and logs.

Health checks:
```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

## Manual (Local) Deployment
```bash
python -m src.orchestration.orchestrator --server --host 0.0.0.0 --port 8000
streamlit run src/interfaces/dashboard.py
```
