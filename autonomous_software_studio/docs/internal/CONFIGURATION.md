# Configuration Reference

## Overview

Autonomous Software Studio uses a layered configuration system with multiple sources:
1. Environment variables (highest priority)
2. `.env` file
3. YAML configuration files
4. Default values (lowest priority)

---

## Environment Variables

### Core API Keys

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | Default API key for all agents |
| `ANTHROPIC_API_KEY_PM` | No | API key for PM agent |
| `ANTHROPIC_API_KEY_ARCH` | No | API key for Architect agent |
| `ANTHROPIC_API_KEY_ENG` | No | API key for Engineer agent |
| `ANTHROPIC_API_KEY_QA` | No | API key for QA agent |

*At least one API key required

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_TYPE` | postgresql | Database type (postgresql, sqlite) |
| `DATABASE_HOST` | postgres | Database host |
| `DATABASE_PORT` | 5432 | Database port |
| `DATABASE_NAME` | softwarestudio | Database name |
| `DATABASE_USER` | softwarestudio | Database user |
| `DATABASE_PASSWORD` | - | Database password (required) |
| `DATABASE_URL` | - | Full connection URL (overrides above) |
| `POSTGRES_USER` | softwarestudio | PostgreSQL user (Docker) |
| `POSTGRES_PASSWORD` | - | PostgreSQL password (Docker) |
| `POSTGRES_DB` | softwarestudio | PostgreSQL database (Docker) |

### Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | redis | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `REDIS_URL` | - | Full Redis URL (overrides above) |

### GitHub Integration

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | - | GitHub Personal Access Token |
| `GH_TOKEN` | - | Alternative GitHub token (fallback) |
| `GITHUB_DEFAULT_ORG` | - | Default organization/username |

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DEBUG_MODE` | false | Enable debug mode |
| `MAX_SESSIONS` | 100 | Maximum concurrent sessions |
| `SESSION_TIMEOUT` | 3600 | Session timeout in seconds |
| `MAX_ITERATIONS` | 5 | Maximum QA-Engineer iterations |
| `SESSION_TTL_DAYS` | 7 | Session time-to-live in days |

### Service Ports

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_PORT` | 8000 | Orchestrator API port |
| `DASHBOARD_PORT` | 8501 | Dashboard UI port |
| `PROMETHEUS_PORT` | 9090 | Prometheus port |
| `GRAFANA_PORT` | 3000 | Grafana port |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `REDIS_PORT` | 6379 | Redis port |

### Claude CLI Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_BINARY` | - | Path to Claude CLI binary |
| `CLAUDE_MODEL` | - | Default model for Claude CLI |
| `CLAUDE_TIMEOUT` | 300 | CLI execution timeout |

### Streamlit Theme

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAMLIT_THEME_BASE` | dark | Base theme (dark, light) |
| `STREAMLIT_THEME_PRIMARY_COLOR` | #00f0ff | Primary accent color |
| `STREAMLIT_THEME_BACKGROUND_COLOR` | #0a0a0f | Background color |
| `STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR` | #12121a | Secondary background |
| `STREAMLIT_THEME_TEXT_COLOR` | #e8e8f0 | Text color |

### Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_USER` | admin | Grafana admin user |
| `GRAFANA_PASSWORD` | admin | Grafana admin password |

### LangChain/LangSmith

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGCHAIN_TRACING_V2` | false | Enable LangSmith tracing |
| `LANGCHAIN_ENDPOINT` | https://api.smith.langchain.com | LangSmith endpoint |
| `LANGCHAIN_API_KEY` | - | LangSmith API key |
| `LANGCHAIN_PROJECT` | autonomous-software-studio | LangSmith project |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | - | Secret key for session management |
| `ENABLE_CORS` | false | Enable CORS |

---

## Configuration Files

### .env File

```bash
# =============================================================================
# Autonomous Software Studio - Environment Configuration
# =============================================================================

# API Keys
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_API_KEY_PM=sk-ant-pm-xxx
ANTHROPIC_API_KEY_ARCH=sk-ant-arch-xxx
ANTHROPIC_API_KEY_ENG=sk-ant-eng-xxx
ANTHROPIC_API_KEY_QA=sk-ant-qa-xxx

# Database
POSTGRES_USER=softwarestudio
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=softwarestudio

# GitHub
GITHUB_TOKEN=ghp_xxx
GITHUB_DEFAULT_ORG=your-org

# Application
LOG_LEVEL=INFO
DEBUG_MODE=false
MAX_SESSIONS=100

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_grafana_password
```

### config/development.yaml

```yaml
orchestrator:
  max_sessions: 20
  session_timeout: 7200
  checkpoint_interval: 60
  log_level: DEBUG

agents:
  timeout: 300
  max_retries: 3

database:
  type: sqlite
  path: data/orchestrator.db

monitoring:
  enabled: false
```

### config/production.yaml

```yaml
orchestrator:
  max_sessions: 100
  session_timeout: 3600
  checkpoint_interval: 60
  log_level: INFO

agents:
  timeout: 300
  max_retries: 3

database:
  type: postgresql
  host: ${DB_HOST}
  port: 5432

monitoring:
  enabled: true
  prometheus_port: 9090
```

### config/testing.yaml

```yaml
orchestrator:
  max_sessions: 5
  session_timeout: 60
  checkpoint_interval: 10
  log_level: DEBUG

agents:
  timeout: 30
  max_retries: 1

database:
  type: sqlite
  path: ":memory:"

monitoring:
  enabled: false
```

---

## Streamlit Configuration

### .streamlit/config.toml

```toml
[global]
developmentMode = false
showWarningOnDirectExecution = false

[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 200
runOnSave = false

[browser]
gatherUsageStats = false
serverAddress = "0.0.0.0"

[theme]
base = "dark"
primaryColor = "#00f0ff"
backgroundColor = "#0a0a0f"
secondaryBackgroundColor = "#12121a"
textColor = "#e8e8f0"
font = "sans serif"

[runner]
magicEnabled = true
installTracer = false
fixMatplotlib = true

[client]
showErrorDetails = true
toolbarMode = "minimal"
```

---

## MCP Server Configuration

### config/mcp_servers.json

```json
{
  "servers": {
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": ["--root", "/app/projects"],
      "env": {}
    },
    "browser": {
      "command": "mcp-server-browser",
      "args": [],
      "env": {}
    },
    "github": {
      "command": "mcp-server-github",
      "args": [],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  },
  "agent_assignments": {
    "pm": ["browser", "github"],
    "arch": ["filesystem", "browser"],
    "eng": ["filesystem", "github"],
    "qa": ["filesystem"]
  }
}
```

---

## Agent Profile Configuration

### config/profiles/pm/settings.yaml

```yaml
profile_name: pm
display_name: Product Manager

provider: anthropic
model: claude-sonnet-4-20250514

auth:
  type: api_key
  env_var: ANTHROPIC_API_KEY_PM

limits:
  daily_limit: 0  # unlimited
  usage_unit: runs
  hard_limit: false

environment:
  CLAUDE_MODEL: claude-sonnet-4-20250514

prompt:
  active: default_prompt.md
  directory: prompts/
```

### config/profiles/eng/settings.yaml

```yaml
profile_name: eng
display_name: Software Engineer

provider: anthropic
model: claude-sonnet-4-20250514

auth:
  type: api_key
  env_var: ANTHROPIC_API_KEY_ENG

limits:
  daily_limit: 100
  usage_unit: runs
  hard_limit: true

environment:
  CLAUDE_MODEL: claude-sonnet-4-20250514
  CLAUDE_TIMEOUT: 600  # Longer timeout for coding

prompt:
  active: default_prompt.md
  directory: prompts/
```

---

## Docker Compose Configuration

### docker-compose.yml Variables

All environment variables can be used in docker-compose.yml with defaults:

```yaml
services:
  orchestrator:
    environment:
      DATABASE_TYPE: ${DATABASE_TYPE:-postgresql}
      DATABASE_HOST: ${DATABASE_HOST:-postgres}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      MAX_SESSIONS: ${MAX_SESSIONS:-100}
```

### Override File

Create `docker-compose.override.yml` for local customizations:

```yaml
version: "3.8"

services:
  orchestrator:
    environment:
      LOG_LEVEL: DEBUG
      DEBUG_MODE: "true"
    volumes:
      - ./src:/app/src  # Mount source for development
```

---

## Prometheus Configuration

### config/prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'autonomous-software-studio'

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'orchestrator'
    static_configs:
      - targets: ['orchestrator:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'dashboard'
    static_configs:
      - targets: ['dashboard:8501']
    metrics_path: '/_stcore/health'
    scrape_interval: 60s
```

---

## Configuration Precedence

Configuration is loaded in this order (later overrides earlier):

1. **Default values** in code
2. **YAML config files** (development/production/testing)
3. **Environment variables** from shell
4. **.env file** in project root
5. **Docker Compose environment** section
6. **Runtime overrides** via API/dashboard

### Example Resolution

```python
# Default in code
MAX_SESSIONS = 50

# production.yaml
max_sessions: 100

# .env file
MAX_SESSIONS=150

# docker-compose.yml
MAX_SESSIONS: ${MAX_SESSIONS:-100}

# Final value: 150 (from .env)
```

---

## Configuration Validation

The system validates configuration on startup:

```python
from src.config.validator import ConfigValidator

validator = ConfigValidator()
errors = validator.validate()

if errors:
    for error in errors:
        logger.error(f"Config error: {error}")
    sys.exit(1)
```

### Required Validations

- At least one API key configured
- Database connection string valid
- All paths exist or can be created
- Port numbers in valid range
- Timeout values positive
