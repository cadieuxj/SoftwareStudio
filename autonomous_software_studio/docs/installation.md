# Installation

## Prerequisites
- Python 3.11+
- Docker (optional, for containerized deployment)
- Node.js (optional, for MCP servers that use `npx`)

## Local Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.template .env
```

Install Claude CLI (required for running agents):
```bash
bash scripts/install_claude_cli.sh
```

## Docker Setup
```bash
docker-compose build
docker-compose up -d
```
