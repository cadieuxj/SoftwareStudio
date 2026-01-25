#!/usr/bin/env python3
"""Compute documentation coverage for required docs."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"

REQUIRED_DOCS = [
    "installation.md",
    "configuration.md",
    "usage.md",
    "architecture.md",
    "api_reference.md",
    "troubleshooting.md",
    "runbooks.md",
    "mcp_integration_guide.md",
]


def main() -> None:
    available = {path.name for path in DOCS_DIR.glob("*.md")}
    covered = [doc for doc in REQUIRED_DOCS if doc in available]
    coverage = (len(covered) / len(REQUIRED_DOCS)) * 100 if REQUIRED_DOCS else 100

    missing = sorted(set(REQUIRED_DOCS) - set(available))
    print(f"Documentation coverage: {coverage:.1f}%")
    if missing:
        print("Missing docs:")
        for doc in missing:
            print(f" - {doc}")
    else:
        print("All required docs present.")


if __name__ == "__main__":
    main()
