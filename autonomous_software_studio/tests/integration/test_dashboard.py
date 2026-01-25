"""Integration tests for the Streamlit dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from src.orchestration.orchestrator import SessionInfo, SessionStatus


APP_PATH = Path(__file__).resolve().parents[2] / "src" / "interfaces" / "dashboard.py"


@dataclass
class RejectCall:
    session_id: str
    feedback: str
    reject_to: str


class FakeOrchestrator:
    """Lightweight orchestrator double for dashboard tests."""

    def __init__(self, base_dir: Path) -> None:
        now = datetime.now()

        prd_path = base_dir / "PRD.md"
        spec_path = base_dir / "TECH_SPEC.md"
        scaffold_path = base_dir / "scaffold.sh"
        bug_report_path = base_dir / "BUG_REPORT.md"
        work_dir = base_dir / "work_dir"
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / "app.py").write_text("print('hello')", encoding="utf-8")

        prd_path.write_text("# PRD\nPRD_FOR_TESTING", encoding="utf-8")
        spec_path.write_text("# TECH SPEC\nSPEC_FOR_TESTING", encoding="utf-8")
        scaffold_path.write_text("#!/usr/bin/env bash\necho scaffold", encoding="utf-8")
        bug_report_path.write_text("# QA Bug Report\nBUG_FOR_TESTING", encoding="utf-8")

        self._artifacts: dict[str, dict[str, Path | None]] = {
            "session-approve": {
                "prd": prd_path,
                "tech_spec": spec_path,
                "scaffold": scaffold_path,
                "bug_report": bug_report_path,
                "work_dir": work_dir,
            },
            "session-running": {
                "prd": prd_path,
                "tech_spec": spec_path,
                "scaffold": scaffold_path,
                "bug_report": None,
                "work_dir": work_dir,
            },
            "session-complete": {
                "prd": prd_path,
                "tech_spec": spec_path,
                "scaffold": None,
                "bug_report": None,
                "work_dir": work_dir,
            },
        }

        self._sessions: dict[str, SessionInfo] = {
            "session-approve": SessionInfo(
                session_id="session-approve",
                user_mission="Ship approval workflow",
                project_name="approval_project",
                status=SessionStatus.AWAITING_APPROVAL,
                current_phase="human_gate",
                created_at=now - timedelta(hours=2),
                updated_at=now - timedelta(minutes=5),
                iteration_count=1,
                qa_passed=False,
                artifacts={},
            ),
            "session-running": SessionInfo(
                session_id="session-running",
                user_mission="Run live execution",
                project_name="live_project",
                status=SessionStatus.RUNNING,
                current_phase="qa",
                created_at=now - timedelta(hours=1),
                updated_at=now - timedelta(minutes=1),
                iteration_count=0,
                qa_passed=False,
                artifacts={},
            ),
            "session-complete": SessionInfo(
                session_id="session-complete",
                user_mission="Complete metrics job",
                project_name="metrics_project",
                status=SessionStatus.COMPLETED,
                current_phase="complete",
                created_at=now - timedelta(days=1),
                updated_at=now - timedelta(hours=1),
                iteration_count=2,
                qa_passed=True,
                artifacts={},
            ),
        }

        self.approve_calls: list[str] = []
        self.reject_calls: list[RejectCall] = []
        self.log_calls: list[str] = []

    def list_sessions(self, status: SessionStatus | None = None, limit: int = 100) -> list[SessionInfo]:
        sessions = list(self._sessions.values())
        if status is not None:
            sessions = [session for session in sessions if session.status == status]
        return sessions[:limit]

    def get_session_status(self, session_id: str) -> SessionInfo:
        return self._sessions[session_id]

    def get_artifacts(self, session_id: str) -> dict[str, Path | None]:
        return self._artifacts[session_id]

    def approve_and_continue(self, session_id: str) -> SessionInfo:
        self.approve_calls.append(session_id)
        info = self._sessions[session_id]
        info.status = SessionStatus.RUNNING
        info.current_phase = "engineer"
        return info

    def reject_and_iterate(self, session_id: str, feedback: str, reject_to: str = "architect") -> SessionInfo:
        self.reject_calls.append(RejectCall(session_id, feedback, reject_to))
        info = self._sessions[session_id]
        info.status = SessionStatus.RUNNING
        info.current_phase = reject_to
        return info

    def get_recent_logs(self, session_id: str, lines: int = 50) -> str:
        self.log_calls.append(session_id)
        return "LOG_LINE_1\nLOG_LINE_2"

    def is_running(self, session_id: str) -> bool:
        return self._sessions[session_id].status == SessionStatus.RUNNING


@pytest.fixture()
def app_with_orchestrator(tmp_path: Path) -> tuple[AppTest, FakeOrchestrator]:
    orchestrator = FakeOrchestrator(tmp_path)
    app = AppTest.from_file(str(APP_PATH))
    app.session_state["orchestrator"] = orchestrator
    return app, orchestrator


@pytest.mark.parametrize(
    ("page", "title"),
    [
        ("Session Management", "Active Sessions"),
        ("Artifact Review", "Review Artifacts"),
        ("Approval Interface", "Approval Interface"),
        ("Live Logs", "Live Execution Logs"),
        ("Metrics & Analytics", "Metrics & Analytics"),
    ],
)
def test_page_rendering(app_with_orchestrator: tuple[AppTest, FakeOrchestrator], page: str, title: str) -> None:
    app, _ = app_with_orchestrator
    app.session_state["nav_page"] = page
    app.run()

    assert any(element.value == title for element in app.title)


def test_artifact_loading(app_with_orchestrator: tuple[AppTest, FakeOrchestrator]) -> None:
    app, _ = app_with_orchestrator
    app.session_state["nav_page"] = "Artifact Review"
    app.session_state["selected_session_id"] = "session-approve"
    app.run()

    assert any("PRD_FOR_TESTING" in element.value for element in app.markdown)


def test_approval_flow(app_with_orchestrator: tuple[AppTest, FakeOrchestrator]) -> None:
    app, orchestrator = app_with_orchestrator
    app.session_state["nav_page"] = "Approval Interface"
    app.session_state["selected_session_id"] = "session-approve"
    app.run()

    approve_button = next(
        button for button in app.button if "Approve" in button.label
    )
    approve_button.click()
    app.run()

    assert orchestrator.approve_calls == ["session-approve"]


def test_rejection_flow(app_with_orchestrator: tuple[AppTest, FakeOrchestrator]) -> None:
    app, orchestrator = app_with_orchestrator
    app.session_state["nav_page"] = "Approval Interface"
    app.session_state["selected_session_id"] = "session-approve"
    app.session_state["feedback_input"] = "Needs more detail."
    app.session_state["reject_phase"] = "PM"
    app.run()

    reject_button = next(
        button for button in app.button if "Submit Feedback" in button.label
    )
    reject_button.click()
    app.run()

    assert orchestrator.reject_calls
    call = orchestrator.reject_calls[0]
    assert call.session_id == "session-approve"
    assert call.feedback == "Needs more detail."
    assert call.reject_to == "pm"


def test_log_streaming(app_with_orchestrator: tuple[AppTest, FakeOrchestrator]) -> None:
    app, orchestrator = app_with_orchestrator
    app.session_state["nav_page"] = "Live Logs"
    app.session_state["selected_session_id"] = "session-running"
    app.run()

    assert orchestrator.log_calls == ["session-running"]
    assert any("LOG_LINE_1" in element.value for element in app.code)
