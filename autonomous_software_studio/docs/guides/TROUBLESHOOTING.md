# Troubleshooting Guide

## Quick Diagnostics

### Check Service Status

```bash
# View all services
docker compose ps

# Expected output (healthy state):
# NAME             STATUS          PORTS
# ass_postgres     Up (healthy)    0.0.0.0:5432->5432/tcp
# ass_redis        Up (healthy)    0.0.0.0:6379->6379/tcp
# ass_orchestrator Up (healthy)    0.0.0.0:8000->8000/tcp
# ass_dashboard    Up (healthy)    0.0.0.0:8501->8501/tcp
```

### Check Logs

```bash
# All services
docker compose logs

# Specific service
docker compose logs orchestrator

# Follow logs in real-time
docker compose logs -f dashboard

# Last 100 lines
docker compose logs --tail 100 orchestrator
```

### Health Endpoints

```bash
# Orchestrator health
curl http://localhost:8000/healthz

# Dashboard health
curl http://localhost:8501/_stcore/health

# PostgreSQL
docker compose exec postgres pg_isready -U softwarestudio

# Redis
docker compose exec redis redis-cli ping
```

---

## Common Issues

### Services Won't Start

#### Issue: Container exits immediately

**Symptoms:**
```
ass_orchestrator exited with code 1
```

**Solutions:**

1. Check logs for error:
   ```bash
   docker compose logs orchestrator
   ```

2. Verify environment variables:
   ```bash
   docker compose config
   ```

3. Check for port conflicts:
   ```bash
   lsof -i :8000
   lsof -i :8501
   ```

4. Rebuild images:
   ```bash
   docker compose build --no-cache
   ```

---

#### Issue: Database connection failed

**Symptoms:**
```
psycopg2.OperationalError: could not connect to server
```

**Solutions:**

1. Wait for PostgreSQL to be ready:
   ```bash
   docker compose up -d postgres
   sleep 10
   docker compose up -d
   ```

2. Check PostgreSQL logs:
   ```bash
   docker compose logs postgres
   ```

3. Verify credentials:
   ```bash
   docker compose exec postgres psql -U softwarestudio -c "SELECT 1;"
   ```

4. Reset database:
   ```bash
   docker compose down -v
   docker compose up -d
   ```

---

#### Issue: Permission denied errors

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: '/app/data'
```

**Solutions:**

1. Fix volume permissions:
   ```bash
   sudo chown -R 1000:1000 data/ logs/ projects/
   ```

2. Or create directories first:
   ```bash
   mkdir -p data logs projects reports docs
   chmod 755 data logs projects reports docs
   ```

---

### Dashboard Issues

#### Issue: Dashboard shows blank page

**Solutions:**

1. Clear browser cache (Ctrl+Shift+R)

2. Check dashboard logs:
   ```bash
   docker compose logs dashboard
   ```

3. Verify Streamlit health:
   ```bash
   curl http://localhost:8501/_stcore/health
   ```

4. Restart dashboard:
   ```bash
   docker compose restart dashboard
   ```

---

#### Issue: Read-only file system error

**Symptoms:**
```
OSError: [Errno 30] Read-only file system: 'data/agent_settings.history'
```

**Solutions:**

1. Verify volume mounts aren't read-only:
   ```yaml
   # docker-compose.yml
   volumes:
     - ./data:/app/data  # NOT ./data:/app/data:ro
   ```

2. Recreate containers:
   ```bash
   docker compose down
   docker compose up -d
   ```

---

#### Issue: Session state not persisting

**Solutions:**

1. Check if browser blocks cookies
2. Try incognito/private mode
3. Clear Streamlit cache:
   ```bash
   docker compose exec dashboard rm -rf /home/appuser/.streamlit/cache
   docker compose restart dashboard
   ```

---

### Session Issues

#### Issue: Session stuck in "pending"

**Solutions:**

1. Check orchestrator logs:
   ```bash
   docker compose logs orchestrator | grep -i error
   ```

2. Verify Claude CLI is installed:
   ```bash
   docker compose exec orchestrator which claude
   docker compose exec orchestrator which claude-code
   ```

3. Test Claude CLI manually:
   ```bash
   docker compose exec orchestrator claude --version
   ```

4. Check API key:
   ```bash
   docker compose exec orchestrator env | grep ANTHROPIC
   ```

---

#### Issue: Session fails immediately

**Symptoms:**
```
Session status: FAILED
Error: Claude CLI execution failed
```

**Solutions:**

1. Check API key is valid:
   ```bash
   curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "content-type: application/json" \
     -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
   ```

2. Check rate limits haven't been exceeded

3. Review agent-specific logs:
   ```bash
   cat logs/pm_agent.log
   ```

---

#### Issue: Session times out

**Symptoms:**
```
AgentTimeoutError: Execution exceeded 300 seconds
```

**Solutions:**

1. Increase timeout in configuration:
   ```yaml
   # config/production.yaml
   agents:
     timeout: 600  # 10 minutes
   ```

2. Or via environment variable:
   ```bash
   CLAUDE_TIMEOUT=600
   ```

3. Check for complex missions that need simplification

---

### Agent Issues

#### Issue: Agent returns empty output

**Solutions:**

1. Check agent prompt is loaded:
   ```bash
   docker compose exec orchestrator cat src/personas/pm_prompt.md
   ```

2. Verify CLAUDE.md is generated:
   ```bash
   ls -la projects/*/CLAUDE.md
   ```

3. Test agent manually:
   ```bash
   docker compose exec orchestrator python -c "
   from src.wrappers.pm_agent import PMAgent
   agent = PMAgent()
   print(agent.get_system_prompt()[:100])
   "
   ```

---

#### Issue: Agent uses wrong model

**Solutions:**

1. Check agent settings in dashboard:
   - Navigate to Agent Account Management
   - Verify model selection

2. Check environment variables:
   ```bash
   docker compose exec orchestrator env | grep MODEL
   ```

3. Override in agent settings:
   ```yaml
   # config/profiles/eng/settings.yaml
   model: claude-opus-4-20250514
   ```

---

### Database Issues

#### Issue: Database migration errors

**Symptoms:**
```
relation "sessions" already exists
```

**Solutions:**

1. Reset database (WARNING: loses data):
   ```bash
   docker compose down -v
   docker compose up -d
   ```

2. Or manually fix:
   ```bash
   docker compose exec postgres psql -U softwarestudio -c "DROP TABLE sessions CASCADE;"
   docker compose restart orchestrator
   ```

---

#### Issue: Database disk full

**Symptoms:**
```
FATAL: could not write to file "pg_wal/..."
```

**Solutions:**

1. Check disk usage:
   ```bash
   docker system df
   ```

2. Clean up old data:
   ```bash
   docker compose exec postgres vacuumdb -U softwarestudio -f -d softwarestudio
   ```

3. Remove old sessions:
   ```bash
   docker compose exec postgres psql -U softwarestudio -c "
   DELETE FROM sessions WHERE created_at < NOW() - INTERVAL '30 days';
   "
   ```

4. Expand volume if needed

---

### Performance Issues

#### Issue: Slow dashboard loading

**Solutions:**

1. Check resource usage:
   ```bash
   docker stats
   ```

2. Increase container resources:
   ```yaml
   services:
     dashboard:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

3. Reduce session list:
   ```bash
   # Clean old sessions
   docker compose exec orchestrator python -m src.orchestration.orchestrator --cleanup
   ```

---

#### Issue: High memory usage

**Solutions:**

1. Limit concurrent sessions:
   ```bash
   MAX_SESSIONS=50
   ```

2. Reduce checkpoint frequency:
   ```yaml
   orchestrator:
     checkpoint_interval: 120  # 2 minutes
   ```

3. Enable Redis for caching:
   ```bash
   docker compose up -d redis
   ```

---

### Network Issues

#### Issue: Services can't communicate

**Symptoms:**
```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solutions:**

1. Check Docker network:
   ```bash
   docker network ls
   docker network inspect autonomous_software_studio_network
   ```

2. Verify service names resolve:
   ```bash
   docker compose exec dashboard ping orchestrator
   docker compose exec orchestrator ping postgres
   ```

3. Recreate network:
   ```bash
   docker compose down
   docker network rm autonomous_software_studio_network
   docker compose up -d
   ```

---

#### Issue: External API calls failing

**Symptoms:**
```
httpx.ConnectError: Unable to connect to api.anthropic.com
```

**Solutions:**

1. Check internet connectivity:
   ```bash
   docker compose exec orchestrator curl -I https://api.anthropic.com
   ```

2. Check DNS resolution:
   ```bash
   docker compose exec orchestrator nslookup api.anthropic.com
   ```

3. Configure proxy if needed:
   ```yaml
   services:
     orchestrator:
       environment:
         HTTP_PROXY: http://proxy:8080
         HTTPS_PROXY: http://proxy:8080
   ```

---

## Diagnostic Commands

### Full System Check

```bash
#!/bin/bash
echo "=== Service Status ==="
docker compose ps

echo "=== Health Checks ==="
curl -s http://localhost:8000/healthz || echo "Orchestrator: FAILED"
curl -s http://localhost:8501/_stcore/health || echo "Dashboard: FAILED"
docker compose exec -T postgres pg_isready -U softwarestudio || echo "PostgreSQL: FAILED"
docker compose exec -T redis redis-cli ping || echo "Redis: FAILED"

echo "=== Resource Usage ==="
docker stats --no-stream

echo "=== Recent Errors ==="
docker compose logs --tail 50 2>&1 | grep -i error

echo "=== Disk Usage ==="
docker system df
```

### Database Status

```bash
docker compose exec postgres psql -U softwarestudio -c "
SELECT
  (SELECT COUNT(*) FROM sessions) as total_sessions,
  (SELECT COUNT(*) FROM sessions WHERE status = 'running') as running,
  (SELECT COUNT(*) FROM sessions WHERE status = 'failed') as failed,
  (SELECT pg_size_pretty(pg_database_size('softwarestudio'))) as db_size;
"
```

### Agent Status

```bash
docker compose exec orchestrator python -c "
from src.orchestration.orchestrator import Orchestrator
o = Orchestrator()
for s in o.list_sessions()[:5]:
    print(f'{s.session_id[:8]}: {s.status.value} ({s.current_phase})')
"
```

---

## Getting Help

### Collecting Debug Information

Before reporting an issue, collect:

```bash
# System info
docker version
docker compose version

# Service logs
docker compose logs > logs.txt 2>&1

# Configuration (remove secrets!)
docker compose config > config.txt

# Database state
docker compose exec postgres pg_dump -U softwarestudio -s > schema.txt
```

### Reporting Issues

Include in your report:
1. Steps to reproduce
2. Expected behavior
3. Actual behavior
4. Logs and error messages
5. Environment details (OS, Docker version)
6. Configuration (sanitized)

### Support Channels

- GitHub Issues: [repository-url]/issues
- Documentation: /docs
- Internal wiki: [wiki-url]
