"""Documentation validation tests."""

from __future__ import annotations

from pathlib import Path


def test_required_docs_exist() -> None:
    docs_dir = Path(__file__).resolve().parents[2] / "docs"
    required = [
        "installation.md",
        "configuration.md",
        "usage.md",
        "architecture.md",
        "api_reference.md",
        "troubleshooting.md",
        "runbooks.md",
        "deployment.md",
    ]
    for doc in required:
        assert (docs_dir / doc).exists(), f"Missing {doc}"


def test_api_reference_mentions_health_endpoints() -> None:
    api_doc = Path(__file__).resolve().parents[2] / "docs" / "api_reference.md"
    content = api_doc.read_text(encoding="utf-8")
    assert "/healthz" in content
    assert "/readyz" in content
    assert "/metrics" in content
