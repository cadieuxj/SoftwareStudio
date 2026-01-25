#!/usr/bin/env bash
set -euo pipefail

echo "=== Deploying Autonomous Software Studio ==="

docker-compose build
docker-compose up -d

echo "Waiting for services to become healthy..."
sleep 5
docker-compose ps

echo "Deployment complete."
