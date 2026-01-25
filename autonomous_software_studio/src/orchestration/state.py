"""LangGraph State Schema and State Management Utilities.

This module defines the LangGraph state schema using TypedDict for type-safe
state management in the multi-agent orchestration pipeline. It provides
state validation, serialization, and checkpoint management.
"""

from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict


class ExecutionLogEntry(TypedDict):
    """Log entry for agent execution."""

    agent: str
    timestamp: str
    status: str  # "started", "completed", "failed"
    duration_seconds: float | None
    tokens_input: int | None
    tokens_output: int | None
    error: str | None


class AgentState(TypedDict, total=False):
    """LangGraph state schema for the multi-agent orchestration pipeline.

    This TypedDict defines the shape of state passed through the LangGraph
    workflow. All fields except user_mission are optional to support
    partial state updates.

    Attributes:
        user_mission: The user's original mission/request (required).
        path_prd: Path to the PRD document.
        path_tech_spec: Path to the technical specification.
        path_scaffold_script: Path to the scaffold.sh script.
        path_bug_report: Path to the QA bug report.
        current_phase: Current pipeline phase (pm, arch, eng, qa, complete, failed).
        qa_passed: Whether QA tests passed.
        iteration_count: Number of QA-Engineer repair cycles.
        max_iterations: Maximum allowed repair cycles.
        architectural_feedback: Accumulated feedback for architecture.
        prd_feedback: Accumulated feedback for PRD.
        session_id: Unique session identifier.
        timestamp: Last update timestamp.
        execution_log: List of execution log entries.
        decision: Human gate decision (APPROVE, REJECT).
        reject_phase: Phase to return to on rejection.
        files_created: List of files created during execution.
        errors: List of errors encountered.
        project_name: Name of the project.
        work_dir: Working directory path.
    """

    # Inputs (required)
    user_mission: str

    # Artifact Paths (File System pointers)
    path_prd: str | None
    path_tech_spec: str | None
    path_scaffold_script: str | None
    path_bug_report: str | None

    # Status Flags
    current_phase: str  # "pm", "arch", "eng", "qa", "complete", "failed"
    qa_passed: bool
    iteration_count: int
    max_iterations: int

    # Human Feedback (Accumulated)
    architectural_feedback: list[str]
    prd_feedback: list[str]

    # Metadata
    session_id: str
    timestamp: str  # ISO format datetime string
    project_name: str
    work_dir: str

    # Execution Logs
    execution_log: list[ExecutionLogEntry]

    # Human Gate Control
    decision: str | None  # "APPROVE", "REJECT", or None
    reject_phase: str | None  # Phase to return to on rejection

    # Tracking
    files_created: list[str]
    errors: list[str]


# Valid phase transitions (from_phase -> allowed_to_phases)
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pm": {"arch", "failed"},
    "arch": {"human_gate", "failed"},
    "human_gate": {"eng", "arch", "pm", "failed"},
    "eng": {"qa", "failed"},
    "qa": {"complete", "eng", "human_help", "failed"},
    "human_help": {"eng", "arch", "pm", "complete", "failed"},
    "complete": set(),  # Terminal state
    "failed": set(),  # Terminal state
}

# Required artifacts for each phase
PHASE_ARTIFACTS: dict[str, list[str]] = {
    "pm": [],  # No prerequisites
    "arch": ["path_prd"],
    "human_gate": ["path_prd", "path_tech_spec"],
    "eng": ["path_prd", "path_tech_spec"],
    "qa": ["path_prd", "path_tech_spec"],
    "complete": ["path_prd", "path_tech_spec"],
}


class StateValidationError(Exception):
    """Raised when state validation fails."""

    pass


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    pass


class StateValidator:
    """Validates LangGraph state transitions and artifacts.

    This class provides methods to validate state transitions,
    check for required artifacts, and verify iteration limits.

    Example:
        >>> validator = StateValidator()
        >>> validator.validate_transition("pm", "arch")
        True
        >>> validator.validate_transition("pm", "qa")
        False
    """

    @staticmethod
    def validate_transition(from_phase: str, to_phase: str) -> bool:
        """Validate that a phase transition is allowed.

        Args:
            from_phase: The current phase.
            to_phase: The target phase.

        Returns:
            True if the transition is valid, False otherwise.
        """
        from_phase = from_phase.lower()
        to_phase = to_phase.lower()

        if from_phase not in VALID_TRANSITIONS:
            return False

        return to_phase in VALID_TRANSITIONS[from_phase]

    @staticmethod
    def validate_artifacts(state: AgentState) -> list[str]:
        """Check for missing artifacts required for the current phase.

        Args:
            state: The current agent state.

        Returns:
            List of missing artifact names.
        """
        current_phase = state.get("current_phase", "pm").lower()
        required = PHASE_ARTIFACTS.get(current_phase, [])

        missing: list[str] = []
        for artifact in required:
            value = state.get(artifact)  # type: ignore[literal-required]
            if value is None:
                missing.append(artifact)

        return missing

    @staticmethod
    def validate_iteration_limit(state: AgentState) -> bool:
        """Check if the iteration limit has been reached.

        Args:
            state: The current agent state.

        Returns:
            True if within limit, False if limit exceeded.
        """
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 5)
        return iteration_count < max_iterations

    @staticmethod
    def validate_state(state: AgentState) -> list[str]:
        """Perform comprehensive state validation.

        Args:
            state: The state to validate.

        Returns:
            List of validation error messages. Empty if valid.
        """
        errors: list[str] = []

        # Check required field
        if not state.get("user_mission"):
            errors.append("user_mission is required and cannot be empty")

        # Check phase validity
        current_phase = state.get("current_phase", "pm")
        valid_phases = set(VALID_TRANSITIONS.keys()) | {"complete", "failed"}
        if current_phase not in valid_phases:
            errors.append(
                f"Invalid current_phase: {current_phase}. "
                f"Must be one of: {', '.join(sorted(valid_phases))}"
            )

        # Check iteration bounds
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 5)
        if iteration_count < 0:
            errors.append("iteration_count cannot be negative")
        if max_iterations < 1:
            errors.append("max_iterations must be at least 1")

        # Check artifacts for current phase
        missing = StateValidator.validate_artifacts(state)
        if missing:
            errors.append(f"Missing required artifacts for phase {current_phase}: {missing}")

        return errors


class ExecutionResult(TypedDict):
    """Result from an agent execution."""

    status: str  # "success", "failure"
    duration_seconds: float
    tokens_input: int
    tokens_output: int
    error: str | None
    artifacts_created: list[str]


class StateManager:
    """Manages LangGraph state updates, serialization, and checkpointing.

    This class provides methods for immutable state updates, execution
    logging, JSON serialization, and checkpoint management.

    Example:
        >>> manager = StateManager()
        >>> state = manager.create_initial_state("Build a task app")
        >>> new_state = manager.update_state(state, {"current_phase": "arch"})
        >>> assert state["current_phase"] == "pm"  # Original unchanged
        >>> assert new_state["current_phase"] == "arch"
    """

    @staticmethod
    def create_initial_state(
        user_mission: str,
        project_name: str = "project",
        work_dir: str | Path | None = None,
        max_iterations: int = 5,
    ) -> AgentState:
        """Create an initial state for a new session.

        Args:
            user_mission: The user's mission/request.
            project_name: Name of the project.
            work_dir: Working directory path.
            max_iterations: Maximum QA-Engineer repair cycles.

        Returns:
            A new AgentState initialized for the PM phase.
        """
        if work_dir is None:
            work_dir = str(Path.cwd())
        elif isinstance(work_dir, Path):
            work_dir = str(work_dir.resolve())

        return AgentState(
            user_mission=user_mission,
            path_prd=None,
            path_tech_spec=None,
            path_scaffold_script=None,
            path_bug_report=None,
            current_phase="pm",
            qa_passed=False,
            iteration_count=0,
            max_iterations=max_iterations,
            architectural_feedback=[],
            prd_feedback=[],
            session_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            project_name=project_name,
            work_dir=work_dir,
            execution_log=[],
            decision=None,
            reject_phase=None,
            files_created=[],
            errors=[],
        )

    @staticmethod
    def update_state(state: AgentState, updates: dict[str, Any]) -> AgentState:
        """Create a new state with updated values (immutable update).

        Args:
            state: The current state.
            updates: Dictionary of fields to update.

        Returns:
            A new AgentState with the updates applied.
        """
        # Deep copy to ensure immutability
        new_state = copy.deepcopy(dict(state))

        # Update timestamp
        new_state["timestamp"] = datetime.now().isoformat()

        # Apply updates
        for key, value in updates.items():
            if isinstance(value, list) and key in new_state:
                # For lists, we might want to append or replace
                # Default behavior: replace
                new_state[key] = copy.deepcopy(value)
            else:
                new_state[key] = copy.deepcopy(value) if isinstance(value, (list, dict)) else value

        return AgentState(**new_state)  # type: ignore[typeddict-item]

    @staticmethod
    def log_execution(
        state: AgentState,
        agent: str,
        result: ExecutionResult,
    ) -> AgentState:
        """Log an agent execution to the state.

        Args:
            state: The current state.
            agent: Name of the agent that executed.
            result: The execution result.

        Returns:
            New state with the execution logged.
        """
        log_entry = ExecutionLogEntry(
            agent=agent,
            timestamp=datetime.now().isoformat(),
            status="completed" if result["status"] == "success" else "failed",
            duration_seconds=result.get("duration_seconds"),
            tokens_input=result.get("tokens_input"),
            tokens_output=result.get("tokens_output"),
            error=result.get("error"),
        )

        new_log = list(state.get("execution_log", []))
        new_log.append(log_entry)

        updates: dict[str, Any] = {"execution_log": new_log}

        # Add created files
        if result.get("artifacts_created"):
            new_files = list(state.get("files_created", []))
            new_files.extend(result["artifacts_created"])
            updates["files_created"] = new_files

        # Add error if present
        if result.get("error"):
            new_errors = list(state.get("errors", []))
            new_errors.append(result["error"])
            updates["errors"] = new_errors

        return StateManager.update_state(state, updates)

    @staticmethod
    def serialize_state(state: AgentState) -> str:
        """Serialize state to JSON string.

        Args:
            state: The state to serialize.

        Returns:
            JSON string representation of the state.
        """
        # Convert to dict for serialization
        state_dict = dict(state)

        return json.dumps(state_dict, indent=2, default=str)

    @staticmethod
    def deserialize_state(json_str: str) -> AgentState:
        """Deserialize state from JSON string.

        Args:
            json_str: JSON string to deserialize.

        Returns:
            The deserialized AgentState.

        Raises:
            ValueError: If the JSON is invalid or missing required fields.
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("State must be a JSON object")

        if "user_mission" not in data:
            raise ValueError("State must contain 'user_mission' field")

        return AgentState(**data)  # type: ignore[typeddict-item]

    @staticmethod
    def save_checkpoint(state: AgentState, path: Path) -> None:
        """Save state to a checkpoint file.

        Args:
            state: The state to save.
            path: Path to the checkpoint file.

        Raises:
            IOError: If the file cannot be written.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint_data = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "state": dict(state),
        }

        # Write atomically
        temp_path = path.with_suffix(".tmp")
        try:
            temp_path.write_text(
                json.dumps(checkpoint_data, indent=2, default=str),
                encoding="utf-8",
            )
            temp_path.replace(path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise IOError(f"Failed to save checkpoint: {e}") from e

    @staticmethod
    def load_checkpoint(path: Path) -> AgentState:
        """Load state from a checkpoint file.

        Args:
            path: Path to the checkpoint file.

        Returns:
            The loaded AgentState.

        Raises:
            FileNotFoundError: If the checkpoint file doesn't exist.
            ValueError: If the checkpoint format is invalid.
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid checkpoint JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("Checkpoint must be a JSON object")

        # Handle both versioned and raw state formats
        if "state" in data:
            state_data = data["state"]
        else:
            state_data = data

        if "user_mission" not in state_data:
            raise ValueError("Checkpoint must contain 'user_mission' field")

        return AgentState(**state_data)  # type: ignore[typeddict-item]

    @staticmethod
    def transition_phase(
        state: AgentState,
        to_phase: str,
        validate: bool = True,
    ) -> AgentState:
        """Transition state to a new phase.

        Args:
            state: The current state.
            to_phase: The target phase.
            validate: Whether to validate the transition.

        Returns:
            New state with updated phase.

        Raises:
            StateTransitionError: If the transition is invalid.
        """
        from_phase = state.get("current_phase", "pm")

        if validate and not StateValidator.validate_transition(from_phase, to_phase):
            raise StateTransitionError(
                f"Invalid transition from '{from_phase}' to '{to_phase}'. "
                f"Valid targets: {VALID_TRANSITIONS.get(from_phase, set())}"
            )

        return StateManager.update_state(state, {"current_phase": to_phase})

    @staticmethod
    def add_feedback(
        state: AgentState,
        feedback: str,
        feedback_type: str,
    ) -> AgentState:
        """Add feedback to the accumulated feedback lists.

        Args:
            state: The current state.
            feedback: The feedback message.
            feedback_type: Either "architectural" or "prd".

        Returns:
            New state with feedback added.

        Raises:
            ValueError: If feedback_type is invalid.
        """
        if feedback_type == "architectural":
            new_feedback = list(state.get("architectural_feedback", []))
            new_feedback.append(feedback)
            return StateManager.update_state(state, {"architectural_feedback": new_feedback})
        elif feedback_type == "prd":
            new_feedback = list(state.get("prd_feedback", []))
            new_feedback.append(feedback)
            return StateManager.update_state(state, {"prd_feedback": new_feedback})
        else:
            raise ValueError(f"Invalid feedback_type: {feedback_type}. Must be 'architectural' or 'prd'")

    @staticmethod
    def increment_iteration(state: AgentState) -> AgentState:
        """Increment the iteration counter.

        Args:
            state: The current state.

        Returns:
            New state with incremented iteration_count.
        """
        current = state.get("iteration_count", 0)
        return StateManager.update_state(state, {"iteration_count": current + 1})


def generate_session_id() -> str:
    """Generate a unique session ID.

    Returns:
        A UUID string for the session.
    """
    return str(uuid.uuid4())
