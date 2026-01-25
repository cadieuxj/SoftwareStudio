#!/usr/bin/env bash
set -euo pipefail

echo "Installing claude-code CLI..."
curl -fsSL https://claude.ai/install.sh | bash

if command -v claude >/dev/null 2>&1; then
  echo "claude CLI installed."
  exit 0
fi

if command -v claude-code >/dev/null 2>&1; then
  echo "claude-code CLI installed."
  exit 0
fi

echo "Claude CLI not found on PATH after install."
echo "Check your shell profile for PATH updates (e.g., ~/.local/bin)."
exit 1
