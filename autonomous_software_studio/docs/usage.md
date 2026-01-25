# Usage

## Start Orchestrator Health Server
```bash
python -m src.orchestration.orchestrator --server --host 0.0.0.0 --port 8000
```

Endpoints:
- `GET /healthz` - Liveness
- `GET /readyz` - Readiness
- `GET /metrics` - Prometheus metrics

## Start Streamlit Dashboard
```bash
streamlit run src/interfaces/dashboard.py
```

## Start a Session from the Dashboard
1. Open the "Session Management" page.
2. Expand "Start New Session".
3. Enter the mission (and optional project name).
4. Click "Start Session" to begin the pipeline.

## Run Tests
```bash
pytest tests/integration/ -v
pytest tests/security/ -v
pytest tests/e2e/ -v
```
