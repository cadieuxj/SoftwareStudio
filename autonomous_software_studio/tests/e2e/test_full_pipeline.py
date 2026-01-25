"""End-to-end tests for the full orchestration pipeline.

These tests use deterministic workflow node doubles to avoid external calls.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestration.orchestrator import Orchestrator, OrchestratorConfig, SessionStatus, SqliteSaver
from src.orchestration.state import StateManager
from src.orchestration.workflow import build_workflow


@pytest.fixture
def sample_mission() -> str:
    return """
    Build a REST API for a task management system with:
    - User authentication (JWT)
    - CRUD operations for tasks
    - Task assignment to users
    - SQLite database
    - FastAPI framework
    - Pytest for testing
    """


@dataclass
class ScenarioConfig:
    qa_failures_before_pass: int = 0
    always_fail: bool = False


class DummyWorkflowNodes:
    """Deterministic workflow nodes for testing orchestration paths."""

    def __init__(self, scenario: ScenarioConfig) -> None:
        self.scenario = scenario
        self._qa_attempts: dict[str, int] = {}
        self._arch_revisions: dict[str, int] = {}

    def _session_id(self, state: dict) -> str:
        return state.get("session_id", "unknown")

    def _work_dir(self, state: dict) -> Path:
        return Path(state.get("work_dir", ".")).resolve()

    def _log(self, state: dict, agent: str, artifacts: list[Path] | None = None, status: str = "success", error: str | None = None) -> dict:
        result = {
            "status": status,
            "duration_seconds": 0.01,
            "tokens_input": 120,
            "tokens_output": 240,
            "error": error,
            "artifacts_created": [str(path) for path in (artifacts or [])],
        }
        return StateManager.log_execution(state, agent, result)

    def pm_node(self, state: dict) -> dict:
        work_dir = self._work_dir(state)
        docs_dir = work_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        prd_path = docs_dir / "PRD.md"
        prd_path.write_text(
            f"# PRD\n\nMission:\n{state.get('user_mission', '').strip()}",
            encoding="utf-8",
        )
        updated = StateManager.update_state(
            state,
            {
                "path_prd": str(prd_path),
                "current_phase": "arch",
            },
        )
        return self._log(updated, "pm", [prd_path])

    def architect_node(self, state: dict) -> dict:
        session_id = self._session_id(state)
        revision = self._arch_revisions.get(session_id, 0) + 1
        self._arch_revisions[session_id] = revision

        work_dir = self._work_dir(state)
        docs_dir = work_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        tech_spec_path = docs_dir / "TECH_SPEC.md"
        tech_spec_path.write_text(
            f"# Tech Spec\n\nRevision: {revision}\n",
            encoding="utf-8",
        )
        scaffold_path = work_dir / "scaffold.sh"
        scaffold_path.write_text("#!/usr/bin/env bash\necho scaffold\n", encoding="utf-8")

        updated = StateManager.update_state(
            state,
            {
                "path_tech_spec": str(tech_spec_path),
                "path_scaffold_script": str(scaffold_path),
                "current_phase": "human_gate",
                "decision": None,
                "reject_phase": None,
            },
        )
        return self._log(updated, "architect", [tech_spec_path, scaffold_path])

    def human_gate_node(self, state: dict) -> dict:
        return state

    def engineer_node(self, state: dict) -> dict:
        work_dir = self._work_dir(state)
        src_dir = work_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        main_path = src_dir / "main.py"
        main_path.write_text(
            "def main():\n    return 'ok'\n",
            encoding="utf-8",
        )
        updated = StateManager.update_state(
            state,
            {
                "current_phase": "qa",
                "files_created": list(state.get("files_created", [])) + [str(main_path)],
            },
        )
        return self._log(updated, "engineer", [main_path])

    def qa_node(self, state: dict) -> dict:
        session_id = self._session_id(state)
        attempt = self._qa_attempts.get(session_id, 0) + 1
        self._qa_attempts[session_id] = attempt

        if self.scenario.always_fail or attempt <= self.scenario.qa_failures_before_pass:
            work_dir = self._work_dir(state)
            reports_dir = work_dir / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            bug_report = reports_dir / "BUG_REPORT.md"
            bug_report.write_text("# QA Bug Report\n\nFailure detected.", encoding="utf-8")

            failed_state = StateManager.update_state(
                state,
                {
                    "qa_passed": False,
                    "path_bug_report": str(bug_report),
                },
            )
            failed_state = StateManager.increment_iteration(failed_state)
            return self._log(failed_state, "qa", [bug_report], status="failure", error="QA failed")

        passed_state = StateManager.update_state(
            state,
            {
                "qa_passed": True,
                "current_phase": "complete",
            },
        )
        return self._log(passed_state, "qa")

    def human_help_node(self, state: dict) -> dict:
        updated = StateManager.update_state(
            state,
            {
                "current_phase": "human_help",
                "qa_passed": False,
            },
        )
        return self._log(updated, "human_help", status="failure", error="Max iterations reached")


def build_orchestrator(
    tmp_path: Path,
    nodes: DummyWorkflowNodes,
    max_iterations: int = 5,
    use_sqlite: bool = False,
) -> Orchestrator:
    config = OrchestratorConfig(
        db_path=tmp_path / "data" / "orchestrator.db",
        max_iterations=max_iterations,
        session_ttl_days=7,
        work_dir_base=tmp_path / "projects",
        use_sqlite_checkpointer=use_sqlite,
    )
    orchestrator = Orchestrator(config)
    orchestrator._workflow_nodes = nodes  # type: ignore[attr-defined]
    orchestrator._graph = build_workflow(nodes=nodes, checkpointer=orchestrator._checkpointer)
    return orchestrator


def wait_for_phase(
    orchestrator: Orchestrator,
    session_id: str,
    phase: str,
    timeout_seconds: float = 2.0,
) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        info = orchestrator.get_session_status(session_id)
        if info.current_phase == phase:
            return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for phase '{phase}' for session {session_id}")


def validate_prd(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    assert "PRD" in content
    assert "Mission" in content


def validate_tech_spec(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    assert "Tech Spec" in content


def validate_code_quality(source_dir: Path) -> None:
    main_path = source_dir / "main.py"
    content = main_path.read_text(encoding="utf-8")
    assert "def main" in content


def assert_execution_metrics(state: dict, phases: list[str]) -> None:
    execution_log = state.get("execution_log", [])
    assert execution_log, "Expected execution log entries."

    logged_agents = {entry.get("agent") for entry in execution_log}
    for phase in phases:
        assert phase in logged_agents, f"Missing metrics for phase: {phase}"

    total_tokens = sum((entry.get("tokens_input") or 0) + (entry.get("tokens_output") or 0) for entry in execution_log)
    total_duration = sum(entry.get("duration_seconds") or 0 for entry in execution_log)
    assert total_tokens > 0
    assert total_duration > 0


def test_happy_path(sample_mission: str, tmp_path: Path) -> None:
    nodes = DummyWorkflowNodes(ScenarioConfig())
    orchestrator = build_orchestrator(tmp_path, nodes)

    session_id = orchestrator.start_new_session(sample_mission)

    wait_for_phase(orchestrator, session_id, "human_gate")
    artifacts = orchestrator.get_artifacts(session_id)

    prd_path = artifacts["prd"]
    tech_spec_path = artifacts["tech_spec"]

    assert prd_path is not None and prd_path.exists()
    assert tech_spec_path is not None and tech_spec_path.exists()
    validate_prd(prd_path)
    validate_tech_spec(tech_spec_path)

    orchestrator.approve_and_continue(session_id)

    info = orchestrator.get_session_status(session_id)
    assert info.status == SessionStatus.COMPLETED
    assert info.qa_passed is True

    work_dir = artifacts["work_dir"]
    assert work_dir is not None
    validate_code_quality(Path(work_dir) / "src")

    state = orchestrator._store.get_state(session_id)
    assert state is not None
    assert_execution_metrics(state, ["pm", "architect", "engineer", "qa"])


def test_human_rejection_architect_phase(sample_mission: str, tmp_path: Path) -> None:
    nodes = DummyWorkflowNodes(ScenarioConfig())
    orchestrator = build_orchestrator(tmp_path, nodes)

    session_id = orchestrator.start_new_session(sample_mission)
    artifacts = orchestrator.get_artifacts(session_id)
    tech_spec_path = artifacts["tech_spec"]
    assert tech_spec_path is not None
    tech_spec_path = Path(tech_spec_path)
    first_revision = tech_spec_path.read_text(encoding="utf-8")

    orchestrator.reject_and_iterate(session_id, "Revise architecture", reject_to="architect")

    info = orchestrator.get_session_status(session_id)
    assert info.status == SessionStatus.AWAITING_APPROVAL
    updated_spec = Path(orchestrator.get_artifacts(session_id)["tech_spec"]).read_text(encoding="utf-8")
    assert updated_spec != first_revision


def test_qa_failure_with_repair_loop(sample_mission: str, tmp_path: Path) -> None:
    nodes = DummyWorkflowNodes(ScenarioConfig(qa_failures_before_pass=1))
    orchestrator = build_orchestrator(tmp_path, nodes)

    session_id = orchestrator.start_new_session(sample_mission)
    orchestrator.approve_and_continue(session_id)

    info = orchestrator.get_session_status(session_id)
    assert info.status == SessionStatus.COMPLETED
    assert info.qa_passed is True

    state = orchestrator._store.get_state(session_id)
    assert state is not None
    assert state.get("iteration_count", 0) == 1


def test_max_iteration_limit_reached(sample_mission: str, tmp_path: Path) -> None:
    nodes = DummyWorkflowNodes(ScenarioConfig(always_fail=True))
    orchestrator = build_orchestrator(tmp_path, nodes, max_iterations=2)

    session_id = orchestrator.start_new_session(sample_mission)
    orchestrator.approve_and_continue(session_id)

    info = orchestrator.get_session_status(session_id)
    assert info.current_phase == "human_help"
    assert info.status == SessionStatus.AWAITING_APPROVAL

    state = orchestrator._store.get_state(session_id)
    assert state is not None
    assert state.get("iteration_count") == 2


def test_checkpoint_resume_after_interrupt(sample_mission: str, tmp_path: Path) -> None:
    use_sqlite = SqliteSaver is not None
    nodes = DummyWorkflowNodes(ScenarioConfig())
    orchestrator = build_orchestrator(tmp_path, nodes, use_sqlite=use_sqlite)

    session_id = orchestrator.start_new_session(sample_mission)

    orchestrator2 = build_orchestrator(tmp_path, DummyWorkflowNodes(ScenarioConfig()), use_sqlite=use_sqlite)
    orchestrator2.approve_and_continue(session_id)

    info = orchestrator2.get_session_status(session_id)
    assert info.status == SessionStatus.COMPLETED
