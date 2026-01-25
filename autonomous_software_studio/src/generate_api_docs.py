"""Generate API reference documentation from OpenAPI spec."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = PROJECT_ROOT / "docs" / "openapi.yaml"
OUTPUT_PATH = PROJECT_ROOT / "docs" / "api_reference.md"


def _load_openapi() -> dict[str, Any]:
    return yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))


def _render_markdown(spec: dict[str, Any]) -> str:
    info = spec.get("info", {})
    lines = [
        "# API Reference",
        "",
        f"**Title:** {info.get('title', 'API')}",
        f"**Version:** {info.get('version', 'unknown')}",
        "",
        "## Endpoints",
        "",
    ]

    paths = spec.get("paths", {})
    for path, methods in paths.items():
        lines.append(f"### `{path}`")
        for method, details in methods.items():
            lines.append(f"- **{method.upper()}** {details.get('summary', '')}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    spec = _load_openapi()
    markdown = _render_markdown(spec)
    OUTPUT_PATH.write_text(markdown, encoding="utf-8")
    print(f"Wrote API reference to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
