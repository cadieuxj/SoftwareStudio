# Autonomous Software Studio

A Multi-Agent Orchestration Pipeline for AI-Powered Software Development

## Overview

Autonomous Software Studio is a fully functional AI software building tool that leverages multiple Claude Code CLI personas orchestrated through LangGraph. The system implements a human-in-the-loop workflow with rigorous QA and testing at every stage.

## Architecture

The system uses a **Multi-Account, Human-in-the-Loop Agentic Pipeline** with four distinct Claude Code CLI personas:

1. **Product Manager (PM)** - Gathers requirements, creates PRDs, manages scope
2. **Architect (ARCH)** - Designs system architecture, creates technical specifications
3. **Engineer (ENG)** - Implements code, follows specifications, writes tests
4. **QA Engineer (QA)** - Tests implementations, validates requirements, reports issues

### Key Features

- **LangGraph Orchestration**: Stateful workflow management with checkpointing
- **Human-in-the-Loop**: Approval gates at critical decision points
- **MCP Integration**: Extensible tool capabilities via Model Context Protocol
- **Streamlit Dashboard**: Real-time monitoring and interaction interface

## Project Structure

```
autonomous_software_studio/
├── src/
│   ├── orchestration/      # LangGraph control plane
│   ├── wrappers/           # Claude CLI wrapper classes
│   ├── personas/           # Agent system prompts
│   └── interfaces/         # Streamlit dashboard
├── docs/                   # Generated artifacts (PRD, specs)
├── tests/
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── config/
│   └── profiles/          # Claude agent profiles
│       ├── pm/
│       ├── arch/
│       ├── eng/
│       └── qa/
├── logs/                  # Execution logs
└── reports/               # QA reports
```

## Installation

### Option 1: Docker (Recommended for Production)

The easiest way to run Autonomous Software Studio is with Docker.

**Prerequisites:**
- Docker 20.10+
- Docker Compose v2+

**Quick Start:**

```bash
# Clone the repository
git clone <repository-url>
cd autonomous_software_studio

# Copy and configure environment variables
cp .env.template .env
# Edit .env with your Anthropic API keys

# Start the application
./scripts/start-docker.sh up

# Or manually with docker compose:
docker compose up -d
```

**Access the services:**
- Dashboard: http://localhost:8501
- Orchestrator API: http://localhost:8000
- Health check: http://localhost:8000/healthz

**With Monitoring (Prometheus + Grafana):**

```bash
./scripts/start-docker.sh up-monitoring

# Or manually:
docker compose --profile monitoring up -d
```

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

**Docker Commands:**

```bash
# View logs
./scripts/start-docker.sh logs

# View specific service logs
./scripts/start-docker.sh logs dashboard

# Stop all services
./scripts/start-docker.sh down

# Rebuild images
./scripts/start-docker.sh build

# Access PostgreSQL shell
./scripts/start-docker.sh db-shell
```

### Option 2: Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd autonomous_software_studio
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp .env.template .env
   # Edit .env with your API keys
   ```

5. Start the services:
   ```bash
   # Terminal 1: Start the orchestrator
   python -m src.orchestration.orchestrator --server

   # Terminal 2: Start the dashboard
   streamlit run src/interfaces/dashboard.py
   ```

## Usage

### Docker Usage (Production)

```bash
# Start the full stack
./scripts/start-docker.sh up

# The dashboard will be available at http://localhost:8501
```

### Local Development

```bash
streamlit run src/interfaces/dashboard.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/
```

## Configuration

### Environment Variables

See `.env.template` for all available configuration options:

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Default API key for all agents | Required |
| `ANTHROPIC_API_KEY_PM` | API key for PM agent | Falls back to default |
| `ANTHROPIC_API_KEY_ARCH` | API key for Architect agent | Falls back to default |
| `ANTHROPIC_API_KEY_ENG` | API key for Engineer agent | Falls back to default |
| `ANTHROPIC_API_KEY_QA` | API key for QA agent | Falls back to default |
| `POSTGRES_PASSWORD` | PostgreSQL password | `securestudiopass` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_SESSIONS` | Maximum concurrent sessions | `100` |

### Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis cache |
| `orchestrator` | 8000 | Main API server |
| `dashboard` | 8501 | Streamlit UI |
| `prometheus` | 9090 | Metrics (optional) |
| `grafana` | 3000 | Monitoring dashboards (optional) |

### UI Theme

The dashboard uses a high-contrast light theme for better readability:
- Dark text (#1a1a1a) on light backgrounds
- Teal accent color (#0f4c5c) for interactive elements
- Clear visual hierarchy for all components

## Development

### Adding a New Persona

1. Create a profile directory in `config/profiles/<persona_name>/`
2. Add system prompt in `src/personas/<persona_name>.py`
3. Register the agent in the LangGraph workflow

### Extending MCP Capabilities

MCP servers can be configured to provide additional tools to agents. See the MCP documentation for integration details.

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.
