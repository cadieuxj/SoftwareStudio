"""Unit tests for LangGraph state management.

Tests cover:
- AgentState initialization
- State updates (immutability)
- Transition validation
- Artifact validation
- Serialization/deserialization
- Checkpoint save/load
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.orchestration.state import (
    PHASE_ARTIFACTS,
    VALID_TRANSITIONS,
    AgentState,
    ExecutionResult,
    StateManager,
    StateTransitionError,
    StateValidator,
    generate_session_id,
)


class TestAgentStateInitialization:
    """Tests for AgentState initialization."""

    def test_create_initial_state_minimal(self) -> None:
        """Test creating state with only required fields."""
        state = StateManager.create_initial_state("Build a task app")

        assert state["user_mission"] == "Build a task app"
        assert state["current_phase"] == "pm"
        assert state["iteration_count"] == 0
        assert state["max_iterations"] == 5
        assert state["qa_passed"] is False
        assert state["path_prd"] is None
        assert state["path_tech_spec"] is None
        assert state["execution_log"] == []
        assert state["errors"] == []

    def test_create_initial_state_with_options(self) -> None:
        """Test creating state with custom options."""
        state = StateManager.create_initial_state(
            user_mission="Build a web app",
            project_name="MyProject",
            work_dir="/tmp/project",
            max_iterations=3,
        )

        assert state["user_mission"] == "Build a web app"
        assert state["project_name"] == "MyProject"
        assert state["work_dir"] == "/tmp/project"
        assert state["max_iterations"] == 3

    def test_create_initial_state_generates_session_id(self) -> None:
        """Test that session_id is generated."""
        state = StateManager.create_initial_state("Test mission")

        assert state["session_id"] is not None
        assert len(state["session_id"]) > 0

    def test_create_initial_state_generates_timestamp(self) -> None:
        """Test that timestamp is set."""
        state = StateManager.create_initial_state("Test mission")

        assert state["timestamp"] is not None
        assert "T" in state["timestamp"]  # ISO format

    def test_create_initial_state_with_path_work_dir(self) -> None:
        """Test creating state with Path work_dir."""
        work_dir = Path("/tmp/test_project")
        state = StateManager.create_initial_state(
            user_mission="Test",
            work_dir=work_dir,
        )

        assert state["work_dir"] == str(work_dir.resolve())


class TestStateImmutability:
    """Tests for state immutability."""

    def test_update_state_creates_new_state(self) -> None:
        """Test that update_state creates a new state object."""
        original = StateManager.create_initial_state("Test mission")
        updated = StateManager.update_state(original, {"current_phase": "arch"})

        assert original is not updated
        assert original["current_phase"] == "pm"
        assert updated["current_phase"] == "arch"

    def test_update_state_preserves_other_fields(self) -> None:
        """Test that update_state preserves unmodified fields."""
        original = StateManager.create_initial_state("Test mission")
        original_session_id = original["session_id"]

        updated = StateManager.update_state(original, {"current_phase": "arch"})

        assert updated["user_mission"] == original["user_mission"]
        assert updated["session_id"] == original_session_id
        assert updated["max_iterations"] == original["max_iterations"]

    def test_update_state_updates_timestamp(self) -> None:
        """Test that update_state updates the timestamp."""
        original = StateManager.create_initial_state("Test mission")
        original_timestamp = original["timestamp"]

        # Small delay to ensure timestamp differs
        import time
        time.sleep(0.01)

        updated = StateManager.update_state(original, {"current_phase": "arch"})

        assert updated["timestamp"] != original_timestamp

    def test_update_state_deep_copies_lists(self) -> None:
        """Test that lists are deep copied."""
        original = StateManager.create_initial_state("Test mission")
        updated = StateManager.update_state(
            original,
            {"errors": ["Error 1"]},
        )

        # Modify the updated state's list
        updated["errors"].append("Error 2")

        # Original should be unchanged
        assert original["errors"] == []

    def test_update_multiple_fields(self) -> None:
        """Test updating multiple fields at once."""
        original = StateManager.create_initial_state("Test mission")
        updated = StateManager.update_state(
            original,
            {
                "current_phase": "arch",
                "path_prd": "/docs/PRD.md",
                "iteration_count": 1,
            },
        )

        assert updated["current_phase"] == "arch"
        assert updated["path_prd"] == "/docs/PRD.md"
        assert updated["iteration_count"] == 1


class TestStateValidator:
    """Tests for StateValidator."""

    def test_validate_transition_valid(self) -> None:
        """Test valid transitions."""
        assert StateValidator.validate_transition("pm", "arch") is True
        assert StateValidator.validate_transition("arch", "human_gate") is True
        assert StateValidator.validate_transition("human_gate", "eng") is True
        assert StateValidator.validate_transition("eng", "qa") is True
        assert StateValidator.validate_transition("qa", "complete") is True

    def test_validate_transition_invalid(self) -> None:
        """Test invalid transitions."""
        assert StateValidator.validate_transition("pm", "qa") is False
        assert StateValidator.validate_transition("pm", "eng") is False
        assert StateValidator.validate_transition("arch", "qa") is False
        assert StateValidator.validate_transition("eng", "arch") is False

    def test_validate_transition_terminal_states(self) -> None:
        """Test that terminal states have no valid transitions."""
        assert StateValidator.validate_transition("complete", "pm") is False
        assert StateValidator.validate_transition("complete", "arch") is False
        assert StateValidator.validate_transition("failed", "pm") is False

    def test_validate_transition_to_failed(self) -> None:
        """Test that any phase can transition to failed."""
        for phase in VALID_TRANSITIONS:
            if phase not in ("complete", "failed"):
                assert StateValidator.validate_transition(phase, "failed") is True

    def test_validate_transition_case_insensitive(self) -> None:
        """Test that transition validation is case insensitive."""
        assert StateValidator.validate_transition("PM", "ARCH") is True
        assert StateValidator.validate_transition("Pm", "Arch") is True

    def test_validate_transition_unknown_phase(self) -> None:
        """Test transition from unknown phase."""
        assert StateValidator.validate_transition("unknown", "arch") is False

    def test_validate_artifacts_pm_phase(self) -> None:
        """Test artifact validation for PM phase (no requirements)."""
        state = StateManager.create_initial_state("Test")
        missing = StateValidator.validate_artifacts(state)
        assert missing == []

    def test_validate_artifacts_arch_phase_missing(self) -> None:
        """Test artifact validation for Architect phase missing PRD."""
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(state, {"current_phase": "arch"})

        missing = StateValidator.validate_artifacts(state)
        assert "path_prd" in missing

    def test_validate_artifacts_arch_phase_complete(self) -> None:
        """Test artifact validation for Architect phase with PRD."""
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(
            state,
            {
                "current_phase": "arch",
                "path_prd": "/docs/PRD.md",
            },
        )

        missing = StateValidator.validate_artifacts(state)
        assert missing == []

    def test_validate_artifacts_eng_phase_missing(self) -> None:
        """Test artifact validation for Engineer phase."""
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(state, {"current_phase": "eng"})

        missing = StateValidator.validate_artifacts(state)
        assert "path_prd" in missing
        assert "path_tech_spec" in missing

    def test_validate_iteration_limit_within(self) -> None:
        """Test iteration limit validation within bounds."""
        state = StateManager.create_initial_state("Test", max_iterations=5)
        state = StateManager.update_state(state, {"iteration_count": 3})

        assert StateValidator.validate_iteration_limit(state) is True

    def test_validate_iteration_limit_at_max(self) -> None:
        """Test iteration limit validation at maximum."""
        state = StateManager.create_initial_state("Test", max_iterations=5)
        state = StateManager.update_state(state, {"iteration_count": 5})

        assert StateValidator.validate_iteration_limit(state) is False

    def test_validate_iteration_limit_exceeded(self) -> None:
        """Test iteration limit validation when exceeded."""
        state = StateManager.create_initial_state("Test", max_iterations=3)
        state = StateManager.update_state(state, {"iteration_count": 10})

        assert StateValidator.validate_iteration_limit(state) is False

    def test_validate_state_valid(self) -> None:
        """Test comprehensive state validation for valid state."""
        state = StateManager.create_initial_state("Build a task app")
        errors = StateValidator.validate_state(state)
        assert errors == []

    def test_validate_state_missing_mission(self) -> None:
        """Test validation catches missing mission."""
        state: AgentState = {"user_mission": ""}  # type: ignore[typeddict-item]
        errors = StateValidator.validate_state(state)
        assert any("user_mission" in e for e in errors)

    def test_validate_state_invalid_phase(self) -> None:
        """Test validation catches invalid phase."""
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(state, {"current_phase": "invalid_phase"})

        errors = StateValidator.validate_state(state)
        assert any("Invalid current_phase" in e for e in errors)

    def test_validate_state_negative_iteration(self) -> None:
        """Test validation catches negative iteration count."""
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(state, {"iteration_count": -1})

        errors = StateValidator.validate_state(state)
        assert any("negative" in e for e in errors)


class TestStateManagerOperations:
    """Tests for StateManager operations."""

    def test_transition_phase_valid(self) -> None:
        """Test valid phase transition."""
        state = StateManager.create_initial_state("Test")
        new_state = StateManager.transition_phase(state, "arch")

        assert new_state["current_phase"] == "arch"
        assert state["current_phase"] == "pm"  # Original unchanged

    def test_transition_phase_invalid_raises(self) -> None:
        """Test invalid phase transition raises error."""
        state = StateManager.create_initial_state("Test")

        with pytest.raises(StateTransitionError):
            StateManager.transition_phase(state, "qa")

    def test_transition_phase_skip_validation(self) -> None:
        """Test transition with validation skipped."""
        state = StateManager.create_initial_state("Test")
        new_state = StateManager.transition_phase(state, "qa", validate=False)

        assert new_state["current_phase"] == "qa"

    def test_add_feedback_architectural(self) -> None:
        """Test adding architectural feedback."""
        state = StateManager.create_initial_state("Test")
        new_state = StateManager.add_feedback(
            state,
            "Consider microservices architecture",
            "architectural",
        )

        assert "Consider microservices architecture" in new_state["architectural_feedback"]
        assert state["architectural_feedback"] == []  # Original unchanged

    def test_add_feedback_prd(self) -> None:
        """Test adding PRD feedback."""
        state = StateManager.create_initial_state("Test")
        new_state = StateManager.add_feedback(
            state,
            "Add more user stories",
            "prd",
        )

        assert "Add more user stories" in new_state["prd_feedback"]

    def test_add_feedback_invalid_type(self) -> None:
        """Test adding feedback with invalid type."""
        state = StateManager.create_initial_state("Test")

        with pytest.raises(ValueError, match="Invalid feedback_type"):
            StateManager.add_feedback(state, "Feedback", "invalid")

    def test_increment_iteration(self) -> None:
        """Test iteration counter increment."""
        state = StateManager.create_initial_state("Test")
        assert state["iteration_count"] == 0

        new_state = StateManager.increment_iteration(state)
        assert new_state["iteration_count"] == 1
        assert state["iteration_count"] == 0  # Original unchanged

    def test_log_execution_success(self) -> None:
        """Test logging successful execution."""
        state = StateManager.create_initial_state("Test")
        result: ExecutionResult = {
            "status": "success",
            "duration_seconds": 10.5,
            "tokens_input": 1000,
            "tokens_output": 500,
            "error": None,
            "artifacts_created": ["/docs/PRD.md"],
        }

        new_state = StateManager.log_execution(state, "PMAgent", result)

        assert len(new_state["execution_log"]) == 1
        assert new_state["execution_log"][0]["agent"] == "PMAgent"
        assert new_state["execution_log"][0]["status"] == "completed"
        assert "/docs/PRD.md" in new_state["files_created"]

    def test_log_execution_failure(self) -> None:
        """Test logging failed execution."""
        state = StateManager.create_initial_state("Test")
        result: ExecutionResult = {
            "status": "failure",
            "duration_seconds": 5.0,
            "tokens_input": 500,
            "tokens_output": 100,
            "error": "API timeout",
            "artifacts_created": [],
        }

        new_state = StateManager.log_execution(state, "PMAgent", result)

        assert new_state["execution_log"][0]["status"] == "failed"
        assert new_state["execution_log"][0]["error"] == "API timeout"
        assert "API timeout" in new_state["errors"]


class TestStateSerialization:
    """Tests for state serialization/deserialization."""

    def test_serialize_state(self) -> None:
        """Test state serialization to JSON."""
        state = StateManager.create_initial_state("Build a task app")
        json_str = StateManager.serialize_state(state)

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["user_mission"] == "Build a task app"

    def test_deserialize_state(self) -> None:
        """Test state deserialization from JSON."""
        json_str = json.dumps({
            "user_mission": "Build a task app",
            "current_phase": "arch",
            "iteration_count": 2,
            "max_iterations": 5,
            "qa_passed": False,
            "session_id": "test-session",
            "timestamp": "2024-01-01T00:00:00",
            "execution_log": [],
            "errors": [],
            "files_created": [],
            "architectural_feedback": [],
            "prd_feedback": [],
        })

        state = StateManager.deserialize_state(json_str)

        assert state["user_mission"] == "Build a task app"
        assert state["current_phase"] == "arch"
        assert state["iteration_count"] == 2

    def test_serialize_deserialize_roundtrip(self) -> None:
        """Test serialization/deserialization round-trip."""
        original = StateManager.create_initial_state("Build a task app")
        original = StateManager.update_state(
            original,
            {
                "current_phase": "arch",
                "path_prd": "/docs/PRD.md",
                "iteration_count": 1,
            },
        )

        json_str = StateManager.serialize_state(original)
        recovered = StateManager.deserialize_state(json_str)

        assert recovered["user_mission"] == original["user_mission"]
        assert recovered["current_phase"] == original["current_phase"]
        assert recovered["path_prd"] == original["path_prd"]
        assert recovered["iteration_count"] == original["iteration_count"]

    def test_deserialize_invalid_json(self) -> None:
        """Test deserialization of invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            StateManager.deserialize_state("not valid json")

    def test_deserialize_missing_mission(self) -> None:
        """Test deserialization without required field."""
        json_str = json.dumps({"current_phase": "pm"})

        with pytest.raises(ValueError, match="user_mission"):
            StateManager.deserialize_state(json_str)

    def test_deserialize_non_object(self) -> None:
        """Test deserialization of non-object JSON."""
        with pytest.raises(ValueError, match="JSON object"):
            StateManager.deserialize_state('"just a string"')

    def test_serialize_with_lists(self) -> None:
        """Test serialization with list fields."""
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(
            state,
            {
                "errors": ["Error 1", "Error 2"],
                "files_created": ["/file1.py", "/file2.py"],
            },
        )

        json_str = StateManager.serialize_state(state)
        recovered = StateManager.deserialize_state(json_str)

        assert recovered["errors"] == ["Error 1", "Error 2"]
        assert recovered["files_created"] == ["/file1.py", "/file2.py"]


class TestCheckpointManagement:
    """Tests for checkpoint save/load functionality."""

    def test_save_checkpoint(self) -> None:
        """Test saving checkpoint to file."""
        state = StateManager.create_initial_state("Build a task app")

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            StateManager.save_checkpoint(state, checkpoint_path)

            assert checkpoint_path.exists()
            content = json.loads(checkpoint_path.read_text())
            assert "version" in content
            assert "saved_at" in content
            assert "state" in content
            assert content["state"]["user_mission"] == "Build a task app"

    def test_load_checkpoint(self) -> None:
        """Test loading checkpoint from file."""
        state = StateManager.create_initial_state("Build a task app")
        state = StateManager.update_state(
            state,
            {
                "current_phase": "arch",
                "path_prd": "/docs/PRD.md",
            },
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            StateManager.save_checkpoint(state, checkpoint_path)

            loaded = StateManager.load_checkpoint(checkpoint_path)

            assert loaded["user_mission"] == state["user_mission"]
            assert loaded["current_phase"] == state["current_phase"]
            assert loaded["path_prd"] == state["path_prd"]

    def test_checkpoint_roundtrip(self) -> None:
        """Test checkpoint save/load preserves all data."""
        state = StateManager.create_initial_state("Build a complex app")
        state = StateManager.update_state(
            state,
            {
                "current_phase": "eng",
                "path_prd": "/docs/PRD.md",
                "path_tech_spec": "/docs/TECH_SPEC.md",
                "iteration_count": 2,
                "errors": ["Warning: deprecated API"],
                "architectural_feedback": ["Use event sourcing"],
            },
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            StateManager.save_checkpoint(state, checkpoint_path)
            loaded = StateManager.load_checkpoint(checkpoint_path)

            assert loaded["user_mission"] == state["user_mission"]
            assert loaded["current_phase"] == state["current_phase"]
            assert loaded["path_prd"] == state["path_prd"]
            assert loaded["path_tech_spec"] == state["path_tech_spec"]
            assert loaded["iteration_count"] == state["iteration_count"]
            assert loaded["errors"] == state["errors"]
            assert loaded["architectural_feedback"] == state["architectural_feedback"]

    def test_load_checkpoint_not_found(self) -> None:
        """Test loading non-existent checkpoint."""
        with pytest.raises(FileNotFoundError):
            StateManager.load_checkpoint(Path("/nonexistent/checkpoint.json"))

    def test_load_checkpoint_invalid_json(self) -> None:
        """Test loading checkpoint with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "bad.json"
            checkpoint_path.write_text("not valid json")

            with pytest.raises(ValueError, match="Invalid checkpoint JSON"):
                StateManager.load_checkpoint(checkpoint_path)

    def test_load_checkpoint_missing_mission(self) -> None:
        """Test loading checkpoint without required field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "incomplete.json"
            checkpoint_path.write_text(json.dumps({
                "version": "1.0",
                "state": {"current_phase": "pm"},
            }))

            with pytest.raises(ValueError, match="user_mission"):
                StateManager.load_checkpoint(checkpoint_path)

    def test_save_checkpoint_creates_directories(self) -> None:
        """Test that save_checkpoint creates parent directories."""
        state = StateManager.create_initial_state("Test")

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "nested" / "dir" / "checkpoint.json"
            StateManager.save_checkpoint(state, checkpoint_path)

            assert checkpoint_path.exists()

    def test_checkpoint_human_readable(self) -> None:
        """Test that checkpoint files are human-readable JSON."""
        state = StateManager.create_initial_state("Build a task app")

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            StateManager.save_checkpoint(state, checkpoint_path)

            content = checkpoint_path.read_text()
            # Check that it's formatted with indentation
            assert "\n  " in content  # Indented


class TestGenerateSessionId:
    """Tests for session ID generation."""

    def test_generate_session_id_format(self) -> None:
        """Test that generated session ID is a valid UUID format."""
        session_id = generate_session_id()

        assert isinstance(session_id, str)
        # UUID format: 8-4-4-4-12 hex characters
        parts = session_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_generate_session_id_unique(self) -> None:
        """Test that generated session IDs are unique."""
        ids = [generate_session_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestValidTransitions:
    """Tests for the VALID_TRANSITIONS constant."""

    def test_all_phases_defined(self) -> None:
        """Test that all phases have transition rules defined."""
        expected_phases = {"pm", "arch", "human_gate", "eng", "qa", "human_help", "complete", "failed"}
        assert set(VALID_TRANSITIONS.keys()) == expected_phases

    def test_repair_loop_exists(self) -> None:
        """Test that QA -> Engineer repair loop is defined."""
        assert "eng" in VALID_TRANSITIONS["qa"]

    def test_human_gate_options(self) -> None:
        """Test human gate can route to multiple phases."""
        human_gate_targets = VALID_TRANSITIONS["human_gate"]
        assert "eng" in human_gate_targets  # Approve
        assert "arch" in human_gate_targets  # Reject to architect
        assert "pm" in human_gate_targets  # Reject to PM


class TestPhaseArtifacts:
    """Tests for the PHASE_ARTIFACTS constant."""

    def test_pm_no_requirements(self) -> None:
        """Test that PM phase has no artifact requirements."""
        assert PHASE_ARTIFACTS["pm"] == []

    def test_arch_requires_prd(self) -> None:
        """Test that Architect phase requires PRD."""
        assert "path_prd" in PHASE_ARTIFACTS["arch"]

    def test_eng_requires_both(self) -> None:
        """Test that Engineer phase requires PRD and tech spec."""
        assert "path_prd" in PHASE_ARTIFACTS["eng"]
        assert "path_tech_spec" in PHASE_ARTIFACTS["eng"]
