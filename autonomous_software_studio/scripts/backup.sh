#!/usr/bin/env bash
set -euo pipefail

backup_dir="backups"
timestamp="$(date +%Y%m%d_%H%M%S)"
archive="${backup_dir}/backup_${timestamp}.tar.gz"

mkdir -p "${backup_dir}"

tar -czf "${archive}" data logs docs reports || true

echo "Backup created: ${archive}"
