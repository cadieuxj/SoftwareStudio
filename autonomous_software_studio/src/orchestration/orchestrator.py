"""Orchestrator for managing LangGraph execution lifecycle.

This module provides the main Orchestrator class that manages sessions,
handles human approvals/rejections, and coordinates the multi-agent pipeline.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Iterator

from langgraph.checkpoint.memory import MemorySaver

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    SqliteSaver = None

from src.orchestration.state import (
    AgentState,
    StateManager,
    StateValidator,
)
from src.orchestration.workflow import WorkflowNodes, build_workflow

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Status of an orchestration session."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""

    pass


class SessionNotFoundError(OrchestratorError):
    """Raised when a session is not found."""

    pass


class SessionExpiredError(OrchestratorError):
    """Raised when a session has expired."""

    pass


class InvalidOperationError(OrchestratorError):
    """Raised when an operation is invalid for current state."""

    pass


@dataclass
class OrchestratorConfig:
    """Configuration for the Orchestrator.

    Attributes:
        db_path: Path to SQLite database for persistence.
        max_iterations: Maximum QA-Engineer repair cycles.
        session_ttl_days: Days until session expires.
        work_dir_base: Base directory for project work directories.
        use_sqlite_checkpointer: Whether to use SQLite for checkpointing.
    """

    db_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("ORCHESTRATOR_DB_PATH", "data/orchestrator.db")
        )
    )
    max_iterations: int = 5
    session_ttl_days: int = 7
    work_dir_base: Path = field(default_factory=lambda: Path("projects"))
    use_sqlite_checkpointer: bool = True


@dataclass
class SessionInfo:
    """Information about a session.

    Attributes:
        session_id: Unique session identifier.
        user_mission: The user's mission/request.
        project_name: Name of the project.
        status: Current session status.
        current_phase: Current workflow phase.
        created_at: When the session was created.
        updated_at: When the session was last updated.
        iteration_count: Number of repair iterations.
        qa_passed: Whether QA tests passed.
        artifacts: Dictionary of artifact paths.
    """

    session_id: str
    user_mission: str
    project_name: str
    status: SessionStatus
    current_phase: str
    created_at: datetime
    updated_at: datetime
    iteration_count: int = 0
    qa_passed: bool = False
    artifacts: dict[str, str | None] = field(default_factory=dict)


class SessionStore:
    """SQLite-based storage for session metadata.

    Thread-safe storage for session information separate from
    LangGraph's checkpointing system.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize the session store.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_mission TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_phase TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    iteration_count INTEGER DEFAULT 0,
                    qa_passed INTEGER DEFAULT 0,
                    work_dir TEXT,
                    state_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_status
                ON sessions(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_updated
                ON sessions(updated_at)
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def save_session(self, session_id: str, state: AgentState) -> None:
        """Save or update session metadata.

        Args:
            session_id: The session identifier.
            state: The current agent state.
        """
        with self._lock:
            with self._get_connection() as conn:
                now = datetime.now().isoformat()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO sessions
                    (session_id, user_mission, project_name, status, current_phase,
                     created_at, updated_at, iteration_count, qa_passed, work_dir, state_json)
                    VALUES (?, ?, ?, ?, ?,
                            COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?),
                            ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        state.get("user_mission", ""),
                        state.get("project_name", "project"),
                        self._determine_status(state).value,
                        state.get("current_phase", "pm"),
                        session_id,
                        now,
                        now,
                        state.get("iteration_count", 0),
                        1 if state.get("qa_passed") else 0,
                        state.get("work_dir", ""),
                        StateManager.serialize_state(state),
                    ),
                )
                conn.commit()

    def get_session(self, session_id: str) -> SessionInfo | None:
        """Get session information.

        Args:
            session_id: The session identifier.

        Returns:
            SessionInfo or None if not found.
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if row is None:
                return None

            return SessionInfo(
                session_id=row["session_id"],
                user_mission=row["user_mission"],
                project_name=row["project_name"],
                status=SessionStatus(row["status"]),
                current_phase=row["current_phase"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                iteration_count=row["iteration_count"],
                qa_passed=bool(row["qa_passed"]),
                artifacts=self._get_artifacts_from_state(row["state_json"]),
            )

    def get_state(self, session_id: str) -> AgentState | None:
        """Get the full state for a session.

        Args:
            session_id: The session identifier.

        Returns:
            AgentState or None if not found.
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT state_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if row is None or row["state_json"] is None:
                return None

            return StateManager.deserialize_state(row["state_json"])

    def update_status(self, session_id: str, status: SessionStatus) -> None:
        """Update session status.

        Args:
            session_id: The session identifier.
            status: The new status.
        """
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE sessions SET status = ?, updated_at = ? WHERE session_id = ?",
                    (status.value, datetime.now().isoformat(), session_id),
                )
                conn.commit()

    def list_sessions(
        self,
        status: SessionStatus | None = None,
        limit: int = 100,
    ) -> list[SessionInfo]:
        """List sessions with optional filtering.

        Args:
            status: Filter by status if provided.
            limit: Maximum number of sessions to return.

        Returns:
            List of SessionInfo objects.
        """
        with self._get_connection() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT * FROM sessions
                    WHERE status = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (status.value, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()

            return [
                SessionInfo(
                    session_id=row["session_id"],
                    user_mission=row["user_mission"],
                    project_name=row["project_name"],
                    status=SessionStatus(row["status"]),
                    current_phase=row["current_phase"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    iteration_count=row["iteration_count"],
                    qa_passed=bool(row["qa_passed"]),
                    artifacts=self._get_artifacts_from_state(row["state_json"]),
                )
                for row in rows
            ]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session identifier.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE session_id = ?",
                    (session_id,),
                )
                conn.commit()
                return cursor.rowcount > 0

    def cleanup_expired(self, ttl_days: int) -> int:
        """Clean up expired sessions.

        Args:
            ttl_days: Number of days after which sessions expire.

        Returns:
            Number of sessions deleted.
        """
        cutoff = (datetime.now() - timedelta(days=ttl_days)).isoformat()

        with self._lock:
            with self._get_connection() as conn:
                # First mark as expired
                conn.execute(
                    """
                    UPDATE sessions
                    SET status = ?
                    WHERE updated_at < ? AND status NOT IN (?, ?)
                    """,
                    (
                        SessionStatus.EXPIRED.value,
                        cutoff,
                        SessionStatus.COMPLETED.value,
                        SessionStatus.EXPIRED.value,
                    ),
                )

                # Then delete old expired sessions
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE updated_at < ? AND status = ?",
                    (cutoff, SessionStatus.EXPIRED.value),
                )
                conn.commit()
                return cursor.rowcount

    def _determine_status(self, state: AgentState) -> SessionStatus:
        """Determine session status from state.

        Args:
            state: The current agent state.

        Returns:
            The appropriate SessionStatus.
        """
        phase = state.get("current_phase", "pm")

        if phase == "complete":
            return SessionStatus.COMPLETED
        elif phase == "failed":
            return SessionStatus.FAILED
        elif phase == "human_gate" or phase == "human_help":
            return SessionStatus.AWAITING_APPROVAL
        else:
            return SessionStatus.RUNNING

    def _get_artifacts_from_state(self, state_json: str | None) -> dict[str, str | None]:
        """Extract artifact paths from state JSON.

        Args:
            state_json: Serialized state JSON.

        Returns:
            Dictionary of artifact names to paths.
        """
        if not state_json:
            return {}

        try:
            state = json.loads(state_json)
            return {
                "prd": state.get("path_prd"),
                "tech_spec": state.get("path_tech_spec"),
                "scaffold": state.get("path_scaffold_script"),
                "bug_report": state.get("path_bug_report"),
            }
        except json.JSONDecodeError:
            return {}


class Orchestrator:
    """Main orchestrator for managing LangGraph execution lifecycle.

    This class provides methods to start sessions, handle human approvals,
    and manage the overall workflow execution.

    Example:
        >>> config = OrchestratorConfig()
        >>> orchestrator = Orchestrator(config)
        >>> session_id = orchestrator.start_new_session("Build a task app")
        >>> status = orchestrator.get_session_status(session_id)
        >>> if status.status == SessionStatus.AWAITING_APPROVAL:
        ...     orchestrator.approve_and_continue(session_id)
    """

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        """Initialize the Orchestrator.

        Args:
            config: Configuration options. Defaults to OrchestratorConfig().
        """
        self.config = config or OrchestratorConfig()
        self._store = SessionStore(self.config.db_path)
        self._workflow_nodes = WorkflowNodes()
        self._lock = threading.Lock()
        self._metrics = {
            "approvals": 0,
            "rejections": 0,
        }

        # Initialize checkpointer
        if self.config.use_sqlite_checkpointer:
            checkpoint_db = self.config.db_path.parent / "checkpoints.db"
            checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
            if SqliteSaver is not None:
                self._checkpointer = SqliteSaver.from_conn_string(str(checkpoint_db))
            else:
                try:
                    from src.orchestration.sqlite_checkpointer import LocalSqliteSaver

                    self._checkpointer = LocalSqliteSaver(checkpoint_db)
                    logger.info("Using local SQLite checkpointer fallback.")
                except Exception as exc:
                    logger.warning(
                        "SqliteSaver unavailable; falling back to MemorySaver. (%s)",
                        exc,
                    )
                    self._checkpointer = MemorySaver()
        else:
            self._checkpointer = MemorySaver()

        # Build workflow
        self._graph = build_workflow(
            nodes=self._workflow_nodes,
            checkpointer=self._checkpointer,
        )

    def start_new_session(
        self,
        user_mission: str,
        project_name: str | None = None,
    ) -> str:
        """Start a new orchestration session.

        Args:
            user_mission: The user's mission/request.
            project_name: Optional project name.

        Returns:
            The session ID for the new session.
        """
        session_id = str(uuid.uuid4())

        if project_name is None:
            # Generate project name from mission
            project_name = self._generate_project_name(user_mission)

        # Create work directory
        work_dir = self.config.work_dir_base / session_id
        work_dir.mkdir(parents=True, exist_ok=True)

        # Initialize state
        state = StateManager.create_initial_state(
            user_mission=user_mission,
            project_name=project_name,
            work_dir=str(work_dir),
            max_iterations=self.config.max_iterations,
        )
        state = StateManager.update_state(state, {"session_id": session_id})

        # Save initial session
        self._store.save_session(session_id, state)

        logger.info(f"Starting new session {session_id} for mission: {user_mission[:50]}...")

        # Execute graph until first interrupt
        thread_config = {"configurable": {"thread_id": session_id}}

        try:
            result = self._graph.invoke(state, config=thread_config)

            # Update session with result
            if isinstance(result, dict):
                self._store.save_session(session_id, result)

            logger.info(f"Session {session_id} reached phase: {result.get('current_phase', 'unknown')}")

        except Exception as e:
            logger.error(f"Session {session_id} failed: {e}")
            error_state = StateManager.update_state(
                state,
                {
                    "current_phase": "failed",
                    "errors": [str(e)],
                },
            )
            self._store.save_session(session_id, error_state)
            raise OrchestratorError(f"Session failed: {e}") from e

        return session_id

    def get_session_status(self, session_id: str) -> SessionInfo:
        """Get the status of a session.

        Args:
            session_id: The session identifier.

        Returns:
            SessionInfo with current status.

        Raises:
            SessionNotFoundError: If session doesn't exist.
        """
        info = self._store.get_session(session_id)

        if info is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        # Check for expiry
        if self._is_expired(info):
            self._store.update_status(session_id, SessionStatus.EXPIRED)
            info.status = SessionStatus.EXPIRED

        return info

    def approve_and_continue(self, session_id: str) -> SessionInfo:
        """Approve the current state and continue execution.

        Args:
            session_id: The session identifier.

        Returns:
            Updated SessionInfo.

        Raises:
            SessionNotFoundError: If session doesn't exist.
            InvalidOperationError: If session is not awaiting approval.
        """
        info = self.get_session_status(session_id)

        if info.status != SessionStatus.AWAITING_APPROVAL:
            raise InvalidOperationError(
                f"Session {session_id} is not awaiting approval. "
                f"Current status: {info.status.value}"
            )

        # Get current state
        state = self._store.get_state(session_id)
        if state is None:
            raise SessionNotFoundError(f"Session state not found: {session_id}")

        logger.info(f"Approving session {session_id}")
        self._metrics["approvals"] += 1

        # Resume execution
        thread_config = {"configurable": {"thread_id": session_id}}

        try:
            # Update state at human gate, then resume execution
            self._graph.update_state(
                thread_config,
                {"decision": "APPROVE", "reject_phase": None},
                as_node="human_gate",
            )
            result = self._graph.invoke(
                None,
                config=thread_config,
            )

            if isinstance(result, dict):
                self._store.save_session(session_id, result)

            return self.get_session_status(session_id)

        except Exception as e:
            logger.error(f"Resume failed for session {session_id}: {e}")
            error_state = StateManager.update_state(
                state,
                {
                    "current_phase": "failed",
                    "errors": list(state.get("errors", [])) + [str(e)],
                },
            )
            self._store.save_session(session_id, error_state)
            raise OrchestratorError(f"Resume failed: {e}") from e

    def reject_and_iterate(
        self,
        session_id: str,
        feedback: str,
        reject_to: str = "architect",
    ) -> SessionInfo:
        """Reject the current state and iterate with feedback.

        Args:
            session_id: The session identifier.
            feedback: Feedback for the rejection.
            reject_to: Phase to return to ("architect" or "pm").

        Returns:
            Updated SessionInfo.

        Raises:
            SessionNotFoundError: If session doesn't exist.
            InvalidOperationError: If session is not awaiting approval.
        """
        info = self.get_session_status(session_id)

        if info.status != SessionStatus.AWAITING_APPROVAL:
            raise InvalidOperationError(
                f"Session {session_id} is not awaiting approval. "
                f"Current status: {info.status.value}"
            )

        # Get current state
        state = self._store.get_state(session_id)
        if state is None:
            raise SessionNotFoundError(f"Session state not found: {session_id}")

        # Add feedback and rejection
        if reject_to == "pm":
            state = StateManager.add_feedback(state, feedback, "prd")
        else:
            state = StateManager.add_feedback(state, feedback, "architectural")

        logger.info(f"Rejecting session {session_id} back to {reject_to}")
        self._metrics["rejections"] += 1

        # Resume execution
        thread_config = {"configurable": {"thread_id": session_id}}

        try:
            updates = {
                "decision": "REJECT",
                "reject_phase": reject_to,
            }
            if reject_to == "pm":
                updates["prd_feedback"] = state.get("prd_feedback", [])
            else:
                updates["architectural_feedback"] = state.get("architectural_feedback", [])

            self._graph.update_state(
                thread_config,
                updates,
                as_node="human_gate",
            )
            result = self._graph.invoke(
                None,
                config=thread_config,
            )

            if isinstance(result, dict):
                self._store.save_session(session_id, result)

            return self.get_session_status(session_id)

        except Exception as e:
            logger.error(f"Rejection failed for session {session_id}: {e}")
            error_state = StateManager.update_state(
                state,
                {
                    "current_phase": "failed",
                    "errors": list(state.get("errors", [])) + [str(e)],
                },
            )
            self._store.save_session(session_id, error_state)
            raise OrchestratorError(f"Rejection failed: {e}") from e

    def get_artifacts(self, session_id: str) -> dict[str, Path | None]:
        """Get artifact paths for a session.

        Args:
            session_id: The session identifier.

        Returns:
            Dictionary of artifact names to paths.

        Raises:
            SessionNotFoundError: If session doesn't exist.
        """
        state = self._store.get_state(session_id)

        if state is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        return {
            "prd": Path(state["path_prd"]) if state.get("path_prd") else None,
            "tech_spec": Path(state["path_tech_spec"]) if state.get("path_tech_spec") else None,
            "scaffold": Path(state["path_scaffold_script"]) if state.get("path_scaffold_script") else None,
            "bug_report": Path(state["path_bug_report"]) if state.get("path_bug_report") else None,
            "work_dir": Path(state["work_dir"]) if state.get("work_dir") else None,
        }

    def get_recent_logs(self, session_id: str, lines: int = 50) -> str:
        """Get recent logs for a session.

        This method first tries to return structured execution logs stored in
        the session state. If none are available, it falls back to tailing
        agent log files from the global logs directory.

        Args:
            session_id: The session identifier.
            lines: Maximum number of log lines to return.

        Returns:
            A string containing recent log lines.

        Raises:
            SessionNotFoundError: If session doesn't exist.
        """
        state = self._store.get_state(session_id)

        if state is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        execution_log = state.get("execution_log", [])
        if execution_log:
            formatted: list[str] = []
            for entry in execution_log[-lines:]:
                formatted.append(
                    f"{entry.get('timestamp', '')} | {entry.get('agent', '')} | "
                    f"{entry.get('status', '')} | {entry.get('error') or ''}".strip()
                )
            return "\n".join(formatted)

        log_dir = Path("logs")
        if not log_dir.exists():
            return ""

        log_files = [
            log_dir / "wrapper_execution.log",
            *sorted(log_dir.glob("agent_*.log")),
        ]

        sections: list[str] = []
        for log_file in log_files:
            if not log_file.exists():
                continue
            try:
                content = log_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            tail = "\n".join(content.splitlines()[-lines:])
            if tail:
                sections.append(f"--- {log_file.name} ---\n{tail}")

        return "\n\n".join(sections)

    def is_running(self, session_id: str) -> bool:
        """Check if a session is currently running.

        Args:
            session_id: The session identifier.

        Returns:
            True if session status is RUNNING.
        """
        info = self.get_session_status(session_id)
        return info.status == SessionStatus.RUNNING

    def list_sessions(
        self,
        status: SessionStatus | None = None,
        limit: int = 100,
    ) -> list[SessionInfo]:
        """List sessions with optional filtering.

        Args:
            status: Filter by status if provided.
            limit: Maximum number of sessions to return.

        Returns:
            List of SessionInfo objects.
        """
        return self._store.list_sessions(status=status, limit=limit)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its data.

        Args:
            session_id: The session identifier.

        Returns:
            True if deleted, False if not found.
        """
        return self._store.delete_session(session_id)

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.

        Returns:
            Number of sessions cleaned up.
        """
        return self._store.cleanup_expired(self.config.session_ttl_days)

    def export_session(self, session_id: str, output_path: Path) -> None:
        """Export session state to a file.

        Args:
            session_id: The session identifier.
            output_path: Path to write the export.

        Raises:
            SessionNotFoundError: If session doesn't exist.
        """
        state = self._store.get_state(session_id)
        info = self._store.get_session(session_id)

        if state is None or info is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "session_info": {
                "session_id": info.session_id,
                "user_mission": info.user_mission,
                "project_name": info.project_name,
                "status": info.status.value,
                "current_phase": info.current_phase,
                "created_at": info.created_at.isoformat(),
                "updated_at": info.updated_at.isoformat(),
            },
            "state": dict(state),
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(export_data, indent=2, default=str),
            encoding="utf-8",
        )

        logger.info(f"Exported session {session_id} to {output_path}")

    def import_session(self, input_path: Path) -> str:
        """Import session state from a file.

        Args:
            input_path: Path to the export file.

        Returns:
            The session ID of the imported session.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If file format is invalid.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Export file not found: {input_path}")

        try:
            data = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid export file: {e}") from e

        if "state" not in data:
            raise ValueError("Export file missing 'state' field")

        state = AgentState(**data["state"])
        session_id = state.get("session_id", str(uuid.uuid4()))

        self._store.save_session(session_id, state)

        logger.info(f"Imported session {session_id} from {input_path}")

        return session_id

    def _generate_project_name(self, mission: str) -> str:
        """Generate a project name from mission.

        Args:
            mission: The user's mission.

        Returns:
            A sanitized project name.
        """
        # Take first few words
        words = mission.split()[:3]
        name = "_".join(words).lower()

        # Remove non-alphanumeric characters
        name = "".join(c if c.isalnum() or c == "_" else "" for c in name)

        # Ensure not empty
        if not name:
            name = "project"

        return name[:50]  # Limit length

    def _is_expired(self, info: SessionInfo) -> bool:
        """Check if a session has expired.

        Args:
            info: Session information.

        Returns:
            True if expired, False otherwise.
        """
        if info.status in (SessionStatus.COMPLETED, SessionStatus.EXPIRED):
            return False

        cutoff = datetime.now() - timedelta(days=self.config.session_ttl_days)
        return info.updated_at < cutoff

    def _build_metrics(self) -> str:
        """Build Prometheus-style metrics output."""
        sessions = self.list_sessions()
        counts: dict[str, int] = {}
        for session in sessions:
            counts[session.status.value] = counts.get(session.status.value, 0) + 1

        lines = [
            "# HELP orchestrator_sessions_total Total number of sessions.",
            "# TYPE orchestrator_sessions_total gauge",
            f"orchestrator_sessions_total {len(sessions)}",
            "# HELP orchestrator_sessions_by_status Sessions grouped by status.",
            "# TYPE orchestrator_sessions_by_status gauge",
        ]
        for status, count in counts.items():
            lines.append(f'orchestrator_sessions_by_status{{status="{status}"}} {count}')

        lines.extend(
            [
                "# HELP orchestrator_approvals_total Total approvals submitted.",
                "# TYPE orchestrator_approvals_total counter",
                f"orchestrator_approvals_total {self._metrics['approvals']}",
                "# HELP orchestrator_rejections_total Total rejections submitted.",
                "# TYPE orchestrator_rejections_total counter",
                f"orchestrator_rejections_total {self._metrics['rejections']}",
            ]
        )
        return "\n".join(lines) + "\n"

    def run_server(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """Run a lightweight health and metrics server."""

        orchestrator = self

        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/healthz":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"ok")
                    return

                if self.path == "/readyz":
                    try:
                        orchestrator.list_sessions(limit=1)
                    except Exception as exc:  # pragma: no cover - defensive
                        self.send_response(503)
                        self.send_header("Content-Type", "text/plain")
                        self.end_headers()
                        self.wfile.write(str(exc).encode("utf-8"))
                        return

                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"ready")
                    return

                if self.path == "/metrics":
                    metrics = orchestrator._build_metrics()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.end_headers()
                    self.wfile.write(metrics.encode("utf-8"))
                    return

                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"not found")

            def log_message(self, format: str, *args: object) -> None:  # noqa: A003
                logger.info("health_server: " + format, *args)

        server = ThreadingHTTPServer((host, port), HealthHandler)
        logger.info("Health server listening on %s:%s", host, port)
        try:
            server.serve_forever()
        finally:
            server.server_close()


def main() -> None:
    """Entry point for testing the orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(description="Orchestrator CLI")
    parser.add_argument(
        "--test-crash-recovery",
        action="store_true",
        help="Test crash recovery functionality",
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List all sessions",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up expired sessions",
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run health and metrics server",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Server host for --server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port for --server",
    )

    args = parser.parse_args()

    config = OrchestratorConfig()
    orchestrator = Orchestrator(config)

    if args.test_crash_recovery:
        print("Testing crash recovery...")
        session_id = orchestrator.start_new_session("Test crash recovery mission")
        print(f"Created session: {session_id}")

        # Simulate crash by creating new orchestrator
        orchestrator2 = Orchestrator(config)
        info = orchestrator2.get_session_status(session_id)
        print(f"Recovered session status: {info.status.value}")
        print("Crash recovery test passed!")

    elif args.list_sessions:
        sessions = orchestrator.list_sessions()
        print(f"Found {len(sessions)} sessions:")
        for session in sessions:
            print(f"  {session.session_id}: {session.status.value} ({session.current_phase})")

    elif args.cleanup:
        count = orchestrator.cleanup_expired_sessions()
        print(f"Cleaned up {count} expired sessions")

    elif args.server:
        orchestrator.run_server(host=args.host, port=args.port)

    else:
        print("Orchestrator CLI")
        print("Use --help for available commands")


if __name__ == "__main__":
    main()
