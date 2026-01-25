#!/usr/bin/env python3
"""Simple load test for the Streamlit dashboard."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from streamlit.testing.v1 import AppTest  # noqa: E402

from src.orchestration.orchestrator import SessionInfo, SessionStatus  # noqa: E402


APP_PATH = Path(__file__).resolve().parents[1] / "src" / "interfaces" / "dashboard.py"


class FakeOrchestrator:
    """Minimal orchestrator for load testing."""

    def __init__(self, session_count: int) -> None:
        now = datetime.now()
        statuses = [
            SessionStatus.RUNNING,
            SessionStatus.AWAITING_APPROVAL,
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
        ]
        self._sessions: list[SessionInfo] = []

        for i in range(session_count):
            status = statuses[i % len(statuses)]
            self._sessions.append(
                SessionInfo(
                    session_id=f"session-{i:03d}",
                    user_mission=f"Load test mission {i}",
                    project_name=f"project_{i}",
                    status=status,
                    current_phase="qa" if status == SessionStatus.RUNNING else "human_gate",
                    created_at=now - timedelta(minutes=i),
                    updated_at=now - timedelta(minutes=i // 2),
                    iteration_count=i % 3,
                    qa_passed=status == SessionStatus.COMPLETED,
                    artifacts={},
                )
            )

    def list_sessions(self, status: SessionStatus | None = None, limit: int = 100) -> list[SessionInfo]:
        sessions = self._sessions
        if status is not None:
            sessions = [session for session in sessions if session.status == status]
        return sessions[:limit]


def run_load_test(session_count: int) -> None:
    """Run a basic render timing test for the dashboard."""
    app = AppTest.from_file(str(APP_PATH))
    app.session_state["orchestrator"] = FakeOrchestrator(session_count)
    app.session_state["nav_page"] = "Session Management"

    start = time.perf_counter()
    app.run()
    elapsed = time.perf_counter() - start

    print(f"Rendered {session_count} sessions in {elapsed:.2f}s")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Dashboard load test")
    parser.add_argument("--sessions", type=int, default=10, help="Number of sessions to simulate")
    args = parser.parse_args()

    run_load_test(args.sessions)


if __name__ == "__main__":
    main()
