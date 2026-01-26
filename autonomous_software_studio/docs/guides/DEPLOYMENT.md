# Deployment Guide

## Overview

This guide covers deploying Autonomous Software Studio in various environments, from local development to production Docker deployments.

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Disk | 20 GB | 50+ GB |
| Docker | 20.10+ | Latest |
| Docker Compose | v2.0+ | Latest |

### Required Accounts/Keys

- **Anthropic API Key** - Required for Claude models
- **GitHub Token** - Optional, for repository integration

---

## Quick Start (Docker)

### 1. Clone Repository

```bash
git clone https://github.com/your-org/autonomous-software-studio.git
cd autonomous-software-studio
```

### 2. Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit with your settings
nano .env
```

**Required Settings:**
```bash
# At minimum, set these:
ANTHROPIC_API_KEY=your_api_key_here
POSTGRES_PASSWORD=your_secure_password
```

### 3. Start Services

```bash
# Using the startup script
./scripts/start-docker.sh up

# Or directly with docker compose
docker compose up -d
```

### 4. Verify Deployment

```bash
# Check service status
docker compose ps

# Check health endpoints
curl http://localhost:8000/healthz
curl http://localhost:8501/_stcore/health
```

### 5. Access Dashboard

Open http://localhost:8501 in your browser.

---

## Deployment Configurations

### Development

Minimal setup for local development.

```bash
# Start with default settings
docker compose up -d postgres redis orchestrator dashboard
```

**Characteristics:**
- PostgreSQL and Redis running locally
- Debug logging enabled
- Hot reload for development
- No monitoring stack

### Production

Full production deployment with monitoring.

```bash
# Start all services including monitoring
docker compose --profile monitoring up -d
```

**Characteristics:**
- All services with health checks
- Prometheus metrics collection
- Grafana dashboards
- Auto-restart on failure
- Volume persistence

### Minimal (No Database)

For testing without persistent storage.

```bash
# Set SQLite mode
DATABASE_TYPE=sqlite docker compose up -d orchestrator dashboard
```

---

## Docker Services

### Service Overview

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| postgres | postgres:16-alpine | 5432 | Primary database |
| redis | redis:7-alpine | 6379 | Session cache |
| orchestrator | custom | 8000 | Main API server |
| dashboard | custom | 8501 | Streamlit UI |
| prometheus | prom/prometheus | 9090 | Metrics (optional) |
| grafana | grafana/grafana | 3000 | Dashboards (optional) |

### Building Images

```bash
# Build all images
docker compose build

# Build specific service
docker compose build orchestrator

# Build without cache
docker compose build --no-cache
```

### Image Details

#### Orchestrator Image

```dockerfile
# Base: python:3.11-slim
# Includes: Node.js 20.x, Claude CLI, PostgreSQL client
# Size: ~800MB
```

Features:
- Claude Code CLI via npm
- Claude CLI via curl
- PostgreSQL client libraries
- Non-root user (appuser)

#### Dashboard Image

```dockerfile
# Base: python:3.11-slim
# Includes: Streamlit, PostgreSQL client
# Size: ~600MB
```

Features:
- Streamlit with futuristic theme
- Read-only access to shared volumes
- Non-root user (appuser)

---

## Environment Variables

### Required Variables

```bash
# Anthropic API (at least one required)
ANTHROPIC_API_KEY=sk-ant-...

# Database
POSTGRES_PASSWORD=secure_password_here
```

### Optional Variables

```bash
# Per-agent API keys (optional, falls back to ANTHROPIC_API_KEY)
ANTHROPIC_API_KEY_PM=sk-ant-...
ANTHROPIC_API_KEY_ARCH=sk-ant-...
ANTHROPIC_API_KEY_ENG=sk-ant-...
ANTHROPIC_API_KEY_QA=sk-ant-...

# GitHub Integration
GITHUB_TOKEN=ghp_...
GITHUB_DEFAULT_ORG=your-org

# Service ports (defaults shown)
ORCHESTRATOR_PORT=8000
DASHBOARD_PORT=8501
POSTGRES_PORT=5432
REDIS_PORT=6379

# Application settings
LOG_LEVEL=INFO
DEBUG_MODE=false
MAX_SESSIONS=100
SESSION_TIMEOUT=3600
```

### Environment File Structure

```bash
# .env file structure
# ===================

# Core API Keys
ANTHROPIC_API_KEY=sk-ant-xxx

# Database
POSTGRES_USER=softwarestudio
POSTGRES_PASSWORD=your_password
POSTGRES_DB=softwarestudio

# Optional integrations
GITHUB_TOKEN=ghp_xxx
GITHUB_DEFAULT_ORG=your-org

# Monitoring (optional)
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin
```

---

## Volume Management

### Persistent Volumes

```yaml
volumes:
  postgres_data:    # Database files
  redis_data:       # Redis persistence
  prometheus_data:  # Metrics history
  grafana_data:     # Dashboard configs
```

### Bind Mounts

```yaml
volumes:
  - ./data:/app/data         # Session data
  - ./logs:/app/logs         # Execution logs
  - ./docs:/app/docs         # Generated docs
  - ./reports:/app/reports   # QA reports
  - ./projects:/app/projects # Work directories
```

### Backup Volumes

```bash
# Backup PostgreSQL
docker compose exec postgres pg_dump -U softwarestudio softwarestudio > backup.sql

# Backup all volumes
docker run --rm -v ass_postgres_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/postgres_backup.tar.gz /data
```

---

## Health Checks

### Orchestrator

```bash
# Check health
curl http://localhost:8000/healthz

# Check readiness
curl http://localhost:8000/readyz

# Expected response
{"status": "healthy", "timestamp": "..."}
```

### Dashboard

```bash
# Check Streamlit health
curl http://localhost:8501/_stcore/health

# Expected response
{"status": "ok"}
```

### PostgreSQL

```bash
# Check database
docker compose exec postgres pg_isready -U softwarestudio

# Expected output
/var/run/postgresql:5432 - accepting connections
```

### Redis

```bash
# Check Redis
docker compose exec redis redis-cli ping

# Expected output
PONG
```

---

## Scaling

### Horizontal Scaling

For high availability, deploy multiple orchestrator instances behind a load balancer.

```yaml
# docker-compose.override.yml
services:
  orchestrator:
    deploy:
      replicas: 3
```

**Requirements:**
- Shared PostgreSQL database
- Shared Redis for session state
- Load balancer (nginx, traefik, etc.)

### Resource Limits

```yaml
services:
  orchestrator:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

---

## SSL/TLS Configuration

### Using Traefik (Recommended)

```yaml
# docker-compose.override.yml
services:
  traefik:
    image: traefik:v2.10
    command:
      - "--providers.docker=true"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./letsencrypt:/letsencrypt

  dashboard:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dashboard.rule=Host(`studio.example.com`)"
      - "traefik.http.routers.dashboard.tls.certresolver=letsencrypt"
```

### Using nginx

```nginx
# /etc/nginx/sites-available/studio
server {
    listen 443 ssl;
    server_name studio.example.com;

    ssl_certificate /etc/letsencrypt/live/studio.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/studio.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /api/ {
        proxy_pass http://localhost:8000/;
    }
}
```

---

## Monitoring

### Enable Monitoring Stack

```bash
# Start with monitoring profile
docker compose --profile monitoring up -d
```

### Prometheus

Access at http://localhost:9090

**Available Metrics:**
- `sessions_total` - Total sessions created
- `sessions_active` - Currently active sessions
- `approvals_total` - Total approvals
- `rejections_total` - Total rejections

### Grafana

Access at http://localhost:3000 (admin/admin)

**Pre-configured Datasources:**
- Prometheus (metrics)
- PostgreSQL (database)

---

## Logging

### Log Locations

```
logs/
├── orchestrator.log    # Main orchestrator logs
├── pm_agent.log        # PM agent logs
├── arch_agent.log      # Architect logs
├── eng_agent.log       # Engineer logs
└── qa_agent.log        # QA logs
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f orchestrator

# Last 100 lines
docker compose logs --tail 100 orchestrator
```

### Log Levels

Set via `LOG_LEVEL` environment variable:
- `DEBUG` - Verbose debugging
- `INFO` - Standard operations
- `WARNING` - Warnings only
- `ERROR` - Errors only

---

## Maintenance

### Database Maintenance

```bash
# Vacuum database
docker compose exec postgres vacuumdb -U softwarestudio -d softwarestudio

# Analyze tables
docker compose exec postgres psql -U softwarestudio -c "ANALYZE;"

# Check database size
docker compose exec postgres psql -U softwarestudio -c "\l+"
```

### Clean Old Sessions

```bash
# Via orchestrator CLI
docker compose exec orchestrator python -m src.orchestration.orchestrator --cleanup
```

### Update Services

```bash
# Pull latest images
docker compose pull

# Rebuild custom images
docker compose build --no-cache

# Restart with new images
docker compose up -d
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs orchestrator

# Check health
docker compose ps

# Restart service
docker compose restart orchestrator
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker compose exec postgres pg_isready

# Check connection string
docker compose exec orchestrator env | grep DATABASE

# Test connection
docker compose exec orchestrator python -c "import psycopg2; psycopg2.connect('...')"
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase limits in docker-compose.yml
# See "Resource Limits" section
```

### Port Conflicts

```bash
# Check what's using the port
lsof -i :8501

# Change port in .env
DASHBOARD_PORT=8502
```

---

## Production Checklist

- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure all API keys
- [ ] Set `LOG_LEVEL=INFO`
- [ ] Set `DEBUG_MODE=false`
- [ ] Configure SSL/TLS
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Test health checks
- [ ] Set resource limits
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Test disaster recovery
