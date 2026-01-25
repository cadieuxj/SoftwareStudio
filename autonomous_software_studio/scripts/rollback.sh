#!/usr/bin/env bash
set -euo pipefail

echo "=== Rolling back Autonomous Software Studio ==="

docker-compose down

echo "Rollback complete."
