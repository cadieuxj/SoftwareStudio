# Operational Runbooks

## Deployment Procedure
```bash
./scripts/deploy.sh
```

## Backup and Recovery
```bash
./scripts/backup.sh
```
To recover, extract the archive into the project directory:
```bash
tar -xzf backups/<backup_file>.tar.gz
```

## Incident Response
1. Check service health: `curl http://localhost:8000/healthz`
2. Inspect logs: `docker-compose logs -f orchestrator`
3. Roll back if needed: `./scripts/rollback.sh`

## Performance Tuning
- Increase `orchestrator.max_sessions` in config for higher concurrency.
- Adjust `agents.timeout` and `agents.max_retries` based on workload.
- Monitor `/metrics` for throughput signals.
