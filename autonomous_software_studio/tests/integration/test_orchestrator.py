"""Integration tests for the Orchestrator.

Tests cover:
- Full session lifecycle
- Concurrent sessions
- Checkpoint persistence
- Approval flow
- Rejection flow
- Session expiry
"""

from __future__ import annotations

import json
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.orchestration.orchestrator import (
    InvalidOperationError,
    Orchestrator,
    OrchestratorConfig,
    OrchestratorError,
    SessionExpiredError,
    SessionInfo,
    SessionNotFoundError,
    SessionStatus,
    SessionStore,
)
from src.orchestration.state import AgentState, StateManager


class TestSessionStore:
    """Tests for SessionStore database operations."""

    def test_init_creates_database(self) -> None:
        """Test that initializing store creates database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SessionStore(db_path)

            assert db_path.exists()

    def test_save_and_get_session(self) -> None:
        """Test saving and retrieving a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SessionStore(db_path)

            state = StateManager.create_initial_state("Test mission")
            session_id = state["session_id"]

            store.save_session(session_id, state)
            info = store.get_session(session_id)

            assert info is not None
            assert info.session_id == session_id
            assert info.user_mission == "Test mission"
            assert info.status == SessionStatus.RUNNING

    def test_get_nonexistent_session(self) -> None:
        """Test getting a session that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SessionStore(db_path)

            info = store.get_session("nonexistent")
            assert info is None

    def test_get_state(self) -> None:
        """Test retrieving full state from store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SessionStore(db_path)

            state = StateManager.create_initial_state("Test mission")
            state = StateManager.update_state(
                state,
                {
                    "current_phase": "arch",
                    "path_prd": "/docs/PRD.md",
                },
            )
            session_id = state["session_id"]

            store.save_session(session_id, state)
            loaded_state = store.get_state(session_id)

            assert loaded_state is not None
            assert loaded_state["current_phase"] == "arch"
            assert loaded_state["path_prd"] == "/docs/PRD.md"

    def test_update_status(self) -> None:
        """Test updating session status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SessionStore(db_path)

            state = StateManager.create_initial_state("Test mission")
            session_id = state["session_id"]

            store.save_session(session_id, state)
            store.update_status(session_id, SessionStatus.COMPLETED)

            info = store.get_session(session_id)
            assert info is not None
            assert info.status == SessionStatus.COMPLETED

    def test_list_sessions(self) -> None:
        """Test listing sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SessionStore(db_path)

            # Create multiple sessions
            for i in range(3):
                state = StateManager.create_initial_state(f"Mission {i}")
                store.save_session(state["session_id"], state)

            sessions = store.list_sessions()
            assert len(sessions) == 3

    def test_list_sessions_with_filter(self) -> None:
        """Test listing sessions with status filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SessionStore(db_path)

            # Create sessions with different statuses
            state1 = StateManager.create_initial_state("Mission 1")
            store.save_session(state1["session_id"], state1)

            state2 = StateManager.create_initial_state("Mission 2")
            state2 = StateManager.update_state(state2, {"current_phase": "complete"})
            store.save_session(state2["session_id"], state2)

            running = store.list_sessions(status=SessionStatus.RUNNING)
            completed = store.list_sessions(status=SessionStatus.COMPLETED)

            assert len(running) == 1
            assert len(completed) == 1

    def test_delete_session(self) -> None:
        """Test deleting a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SessionStore(db_path)

            state = StateManager.create_initial_state("Test mission")
            session_id = state["session_id"]

            store.save_session(session_id, state)
            assert store.get_session(session_id) is not None

            result = store.delete_session(session_id)
            assert result is True
            assert store.get_session(session_id) is None

    def test_delete_nonexistent_session(self) -> None:
        """Test deleting a session that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SessionStore(db_path)

            result = store.delete_session("nonexistent")
            assert result is False

    def test_status_determination(self) -> None:
        """Test that status is correctly determined from state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = SessionStore(db_path)

            # Test complete status
            state = StateManager.create_initial_state("Test")
            state = StateManager.update_state(state, {"current_phase": "complete"})
            store.save_session("test1", state)
            assert store.get_session("test1").status == SessionStatus.COMPLETED

            # Test failed status
            state = StateManager.create_initial_state("Test")
            state = StateManager.update_state(state, {"current_phase": "failed"})
            store.save_session("test2", state)
            assert store.get_session("test2").status == SessionStatus.FAILED

            # Test awaiting approval
            state = StateManager.create_initial_state("Test")
            state = StateManager.update_state(state, {"current_phase": "human_gate"})
            store.save_session("test3", state)
            assert store.get_session("test3").status == SessionStatus.AWAITING_APPROVAL


class TestOrchestratorConfig:
    """Tests for OrchestratorConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = OrchestratorConfig()

        assert config.max_iterations == 5
        assert config.session_ttl_days == 7
        assert config.use_sqlite_checkpointer is True

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = OrchestratorConfig(
            max_iterations=3,
            session_ttl_days=14,
            use_sqlite_checkpointer=False,
        )

        assert config.max_iterations == 3
        assert config.session_ttl_days == 14
        assert config.use_sqlite_checkpointer is False


class TestOrchestratorInit:
    """Tests for Orchestrator initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initializing orchestrator with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                work_dir_base=Path(tmpdir) / "projects",
                use_sqlite_checkpointer=False,  # Use memory for tests
            )
            orchestrator = Orchestrator(config)

            assert orchestrator.config == config
            assert orchestrator._graph is not None

    def test_init_creates_directories(self) -> None:
        """Test that initialization creates necessary directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nested" / "dir" / "test.db"
            config = OrchestratorConfig(
                db_path=db_path,
                use_sqlite_checkpointer=False,
            )
            Orchestrator(config)

            assert db_path.parent.exists()


class TestOrchestratorSessions:
    """Tests for session management."""

    @patch("src.orchestration.workflow.WorkflowNodes._get_architect_agent")
    @patch("src.orchestration.workflow.WorkflowNodes._get_pm_agent")
    def test_start_new_session(
        self,
        mock_get_pm: MagicMock,
        mock_get_arch: MagicMock,
    ) -> None:
        """Test starting a new session."""
        from src.wrappers.state import AgentState as WrapperState

        # Mock PM agent
        mock_pm = MagicMock()
        mock_pm.execute.return_value = WrapperState(
            mission="Test",
            current_phase="arch",
            path_prd=Path("/docs/PRD.md"),
        )
        mock_get_pm.return_value = mock_pm

        # Mock Architect agent
        mock_arch = MagicMock()
        mock_arch.execute.return_value = WrapperState(
            mission="Test",
            current_phase="eng",
            path_prd=Path("/docs/PRD.md"),
            path_tech_spec=Path("/docs/TECH_SPEC.md"),
        )
        mock_get_arch.return_value = mock_arch

        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                work_dir_base=Path(tmpdir) / "projects",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            session_id = orchestrator.start_new_session("Build a task app")

            assert session_id is not None
            assert len(session_id) > 0

            # Check session was saved
            info = orchestrator.get_session_status(session_id)
            assert info.user_mission == "Build a task app"
            # Session should be awaiting approval at human_gate
            assert info.status == SessionStatus.AWAITING_APPROVAL

    def test_get_session_status_not_found(self) -> None:
        """Test getting status for nonexistent session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            with pytest.raises(SessionNotFoundError):
                orchestrator.get_session_status("nonexistent")

    def test_delete_session(self) -> None:
        """Test deleting a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            # Manually add a session
            state = StateManager.create_initial_state("Test")
            orchestrator._store.save_session("test-session", state)

            result = orchestrator.delete_session("test-session")
            assert result is True

            with pytest.raises(SessionNotFoundError):
                orchestrator.get_session_status("test-session")

    def test_list_sessions(self) -> None:
        """Test listing sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            # Add some sessions manually
            for i in range(3):
                state = StateManager.create_initial_state(f"Mission {i}")
                orchestrator._store.save_session(f"session-{i}", state)

            sessions = orchestrator.list_sessions()
            assert len(sessions) == 3


class TestOrchestratorApproval:
    """Tests for approval/rejection flows."""

    def test_approve_not_awaiting(self) -> None:
        """Test approving a session not awaiting approval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            # Add a running session
            state = StateManager.create_initial_state("Test")
            orchestrator._store.save_session("test-session", state)

            with pytest.raises(InvalidOperationError):
                orchestrator.approve_and_continue("test-session")

    def test_reject_not_awaiting(self) -> None:
        """Test rejecting a session not awaiting approval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            # Add a running session
            state = StateManager.create_initial_state("Test")
            orchestrator._store.save_session("test-session", state)

            with pytest.raises(InvalidOperationError):
                orchestrator.reject_and_iterate("test-session", "Feedback")


class TestOrchestratorArtifacts:
    """Tests for artifact management."""

    def test_get_artifacts(self) -> None:
        """Test getting artifacts for a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            # Add session with artifacts
            state = StateManager.create_initial_state("Test")
            state = StateManager.update_state(
                state,
                {
                    "path_prd": "/docs/PRD.md",
                    "path_tech_spec": "/docs/TECH_SPEC.md",
                    "work_dir": "/projects/test",
                },
            )
            orchestrator._store.save_session("test-session", state)

            artifacts = orchestrator.get_artifacts("test-session")

            assert artifacts["prd"] == Path("/docs/PRD.md")
            assert artifacts["tech_spec"] == Path("/docs/TECH_SPEC.md")
            assert artifacts["work_dir"] == Path("/projects/test")

    def test_get_artifacts_not_found(self) -> None:
        """Test getting artifacts for nonexistent session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            with pytest.raises(SessionNotFoundError):
                orchestrator.get_artifacts("nonexistent")


class TestOrchestratorExportImport:
    """Tests for session export/import."""

    def test_export_session(self) -> None:
        """Test exporting a session to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            # Add a session
            state = StateManager.create_initial_state("Test mission")
            orchestrator._store.save_session("test-session", state)

            export_path = Path(tmpdir) / "export.json"
            orchestrator.export_session("test-session", export_path)

            assert export_path.exists()
            data = json.loads(export_path.read_text())
            assert data["session_info"]["session_id"] == "test-session"
            assert data["state"]["user_mission"] == "Test mission"

    def test_import_session(self) -> None:
        """Test importing a session from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            # Create export file
            export_data = {
                "version": "1.0",
                "state": {
                    "user_mission": "Imported mission",
                    "session_id": "imported-session",
                    "current_phase": "pm",
                    "project_name": "test",
                    "work_dir": "/tmp",
                    "iteration_count": 0,
                    "max_iterations": 5,
                    "qa_passed": False,
                    "errors": [],
                    "files_created": [],
                    "execution_log": [],
                    "architectural_feedback": [],
                    "prd_feedback": [],
                    "timestamp": datetime.now().isoformat(),
                },
            }
            import_path = Path(tmpdir) / "import.json"
            import_path.write_text(json.dumps(export_data))

            session_id = orchestrator.import_session(import_path)

            assert session_id == "imported-session"
            info = orchestrator.get_session_status(session_id)
            assert info.user_mission == "Imported mission"

    def test_import_file_not_found(self) -> None:
        """Test importing from nonexistent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            with pytest.raises(FileNotFoundError):
                orchestrator.import_session(Path("/nonexistent/file.json"))

    def test_import_invalid_file(self) -> None:
        """Test importing from invalid file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            import_path = Path(tmpdir) / "invalid.json"
            import_path.write_text("not valid json")

            with pytest.raises(ValueError):
                orchestrator.import_session(import_path)


class TestOrchestratorExpiry:
    """Tests for session expiry."""

    def test_cleanup_expired_sessions(self) -> None:
        """Test cleaning up expired sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                session_ttl_days=7,
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            # Add an old session by manipulating the timestamp
            state = StateManager.create_initial_state("Old mission")
            orchestrator._store.save_session("old-session", state)

            # Manually update the timestamp to be old
            with orchestrator._store._get_connection() as conn:
                old_time = (datetime.now() - timedelta(days=10)).isoformat()
                conn.execute(
                    "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                    (old_time, "old-session"),
                )
                conn.commit()

            count = orchestrator.cleanup_expired_sessions()
            # First cleanup marks as expired, second deletes
            count = orchestrator.cleanup_expired_sessions()

            # Session should be gone
            info = orchestrator._store.get_session("old-session")
            assert info is None or info.status == SessionStatus.EXPIRED


class TestConcurrentSessions:
    """Tests for concurrent session handling."""

    def test_concurrent_session_creation(self) -> None:
        """Test creating sessions concurrently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            session_ids: list[str] = []
            errors: list[Exception] = []

            def create_session(mission: str) -> None:
                try:
                    state = StateManager.create_initial_state(mission)
                    orchestrator._store.save_session(state["session_id"], state)
                    session_ids.append(state["session_id"])
                except Exception as e:
                    errors.append(e)

            threads = [
                threading.Thread(target=create_session, args=(f"Mission {i}",))
                for i in range(10)
            ]

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0
            assert len(session_ids) == 10
            assert len(set(session_ids)) == 10  # All unique


class TestProjectNameGeneration:
    """Tests for project name generation."""

    def test_generate_project_name_simple(self) -> None:
        """Test generating project name from simple mission."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            name = orchestrator._generate_project_name("Build a task app")
            assert name == "build_a_task"

    def test_generate_project_name_special_chars(self) -> None:
        """Test generating project name with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            name = orchestrator._generate_project_name("Build a web-app!")
            assert "build" in name
            assert "!" not in name

    def test_generate_project_name_empty(self) -> None:
        """Test generating project name from empty string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            name = orchestrator._generate_project_name("")
            assert name == "project"

    def test_generate_project_name_long(self) -> None:
        """Test generating project name from long mission."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OrchestratorConfig(
                db_path=Path(tmpdir) / "test.db",
                use_sqlite_checkpointer=False,
            )
            orchestrator = Orchestrator(config)

            long_mission = "Build " + "x" * 100 + " application"
            name = orchestrator._generate_project_name(long_mission)
            assert len(name) <= 50
