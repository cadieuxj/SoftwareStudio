#!/usr/bin/env python3
"""Generate lightweight SVG placeholders for dashboard screenshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Block:
    label: str
    x: int
    y: int
    width: int
    height: int


def render_svg(title: str, subtitle: str, blocks: list[Block]) -> str:
    """Render a simple SVG layout with labeled blocks."""
    width = 1400
    height = 900

    block_markup = "\n".join(
        f"""
        <g>
            <rect x="{block.x}" y="{block.y}" width="{block.width}" height="{block.height}" rx="18"
                  fill="rgba(255,255,255,0.85)" stroke="rgba(15,76,92,0.25)" stroke-width="2"/>
            <text x="{block.x + 20}" y="{block.y + 38}" font-size="20" fill="#1b1b1d"
                  font-family="Arial, sans-serif">{block.label}</text>
        </g>
        """
        for block in blocks
    )

    return f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
         xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stop-color="#f7f1e1" />
                <stop offset="55%" stop-color="#eef4f6" />
                <stop offset="100%" stop-color="#f7fafc" />
            </linearGradient>
        </defs>
        <rect width="{width}" height="{height}" fill="url(#bg)"/>
        <text x="80" y="80" font-size="34" fill="#0f4c5c" font-family="Arial, sans-serif">{title}</text>
        <text x="80" y="110" font-size="18" fill="#5f646b" font-family="Arial, sans-serif">{subtitle}</text>
        {block_markup}
    </svg>
    """.strip()


def write_svg(path: Path, svg: str) -> None:
    """Write SVG content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")


def main() -> None:
    """Generate placeholder screenshots for each dashboard page."""
    output_dir = Path(__file__).resolve().parents[1] / "docs" / "screenshots"

    pages = {
        "session_management.svg": (
            "Session Management",
            "Active sessions and kanban view",
            [
                Block("Active Sessions", 80, 150, 600, 280),
                Block("Session Detail", 720, 150, 600, 280),
                Block("Kanban Board", 80, 470, 1240, 330),
            ],
        ),
        "artifact_review.svg": (
            "Artifact Review",
            "PRD, Tech Spec, and Code tabs",
            [
                Block("Session Selector", 80, 150, 1240, 120),
                Block("PRD Tab", 80, 300, 400, 420),
                Block("Tech Spec Tab", 520, 300, 400, 420),
                Block("Code Tab", 960, 300, 360, 420),
            ],
        ),
        "approval_interface.svg": (
            "Approval Interface",
            "Approve or request changes",
            [
                Block("Session Status", 80, 150, 600, 220),
                Block("Approve & Build", 720, 150, 600, 220),
                Block("Request Changes", 80, 410, 1240, 340),
            ],
        ),
        "live_logs.svg": (
            "Live Logs",
            "Streaming execution output",
            [
                Block("Session Selector", 80, 150, 1240, 120),
                Block("Log Stream", 80, 300, 1240, 470),
            ],
        ),
        "metrics_analytics.svg": (
            "Metrics & Analytics",
            "Operational and quality metrics",
            [
                Block("Top Metrics", 80, 150, 1240, 200),
                Block("Status Breakdown", 80, 380, 600, 360),
                Block("Quality Signals", 720, 380, 600, 360),
            ],
        ),
    }

    for filename, (title, subtitle, blocks) in pages.items():
        svg = render_svg(title, subtitle, blocks)
        write_svg(output_dir / filename, svg)

    print(f"Generated {len(pages)} screenshot placeholders in {output_dir}")


if __name__ == "__main__":
    main()
