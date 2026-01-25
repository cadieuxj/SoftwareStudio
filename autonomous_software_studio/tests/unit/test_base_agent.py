"""Unit tests for BaseAgent abstract class and AgentState model.

Tests cover:
- Abstract class cannot be instantiated
- Subclass implementation validation
- System prompt loading
- State immutability enforcement
- Artifact validation logic
- Execution metrics calculation
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.wrappers.base_agent import (
    AgentError,
    ArtifactValidationError,
    BaseAgent,
    MockAgent,
    PromptLoadError,
    StateValidationError,
)
from src.wrappers.state import (
    AgentState,
    ExecutionMetrics,
    create_initial_state,
)


class TestAgentState:
    """Tests for AgentState Pydantic model."""

    def test_create_initial_state(self) -> None:
        """Test creating initial state with factory function."""
        state = create_initial_state(
            mission="Build a task management app",
            project_name="TaskApp",
        )

        assert state.mission == "Build a task management app"
        assert state.project_name == "TaskApp"
        assert state.current_phase == "pm"
        assert state.qa_passed is None
        assert len(state.errors) == 0
        assert len(state.files_created) == 0

    def test_state_immutability(self) -> None:
        """Test that AgentState is frozen (immutable)."""
        state = create_initial_state(mission="Test mission")

        # Attempting to modify should raise an error
        with pytest.raises(ValidationError):
            state.mission = "New mission"  # type: ignore

        with pytest.raises(ValidationError):
            state.current_phase = "arch"  # type: ignore

    def test_state_with_update_creates_new_instance(self) -> None:
        """Test that with_update creates a new state instance."""
        original = create_initial_state(mission="Original mission")
        updated = original.with_update(current_phase="arch")

        # Original should be unchanged
        assert original.current_phase == "pm"

        # Updated should have new value
        assert updated.current_phase == "arch"

        # Should be different instances
        assert original is not updated

    def test_state_with_update_preserves_values(self) -> None:
        """Test that with_update preserves unmodified values."""
        original = create_initial_state(
            mission="Test mission",
            project_name="TestProject",
        )

        updated = original.with_update(current_phase="arch")

        assert updated.mission == original.mission
        assert updated.project_name == original.project_name

    def test_state_phase_validation(self) -> None:
        """Test that invalid phases are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            create_initial_state(mission="Test").with_update(current_phase="invalid")

        assert "Invalid phase" in str(exc_info.value)

    def test_state_valid_phases(self) -> None:
        """Test all valid phase transitions."""
        state = create_initial_state(mission="Test")

        for phase in ["pm", "arch", "eng", "qa", "complete", "failed"]:
            new_state = state.with_update(current_phase=phase)
            assert new_state.current_phase == phase

    def test_add_file(self) -> None:
        """Test adding files to state."""
        state = create_initial_state(mission="Test")
        new_path = Path("/tmp/test.py")

        new_state = state.add_file(new_path)

        assert new_path in new_state.files_created
        assert len(new_state.files_created) == 1
        assert len(state.files_created) == 0  # Original unchanged

    def test_add_file_no_duplicates(self) -> None:
        """Test that duplicate files are not added."""
        state = create_initial_state(mission="Test")
        path = Path("/tmp/test.py")

        state = state.add_file(path)
        state = state.add_file(path)  # Add again

        assert len(state.files_created) == 1

    def test_add_files_multiple(self) -> None:
        """Test adding multiple files at once."""
        state = create_initial_state(mission="Test")
        paths = [Path("/tmp/a.py"), Path("/tmp/b.py"), Path("/tmp/c.py")]

        new_state = state.add_files(paths)

        assert len(new_state.files_created) == 3
        for path in paths:
            assert path in new_state.files_created

    def test_add_error(self) -> None:
        """Test adding errors to state."""
        state = create_initial_state(mission="Test")

        new_state = state.add_error("Something went wrong")

        assert len(new_state.errors) == 1
        assert "Something went wrong" in new_state.errors
        assert len(state.errors) == 0  # Original unchanged

    def test_add_execution(self) -> None:
        """Test recording execution metrics."""
        state = create_initial_state(mission="Test")
        metrics = ExecutionMetrics(
            tokens_input=100,
            tokens_output=200,
            execution_time_seconds=5.0,
            estimated_cost_usd=0.01,
        )

        new_state = state.add_execution(metrics, "test_agent")

        assert len(new_state.execution_history) == 1
        assert new_state.execution_history[0]["agent"] == "test_agent"
        assert new_state.execution_history[0]["metrics"]["tokens_input"] == 100

    def test_transition_to_phase(self) -> None:
        """Test phase transition helper."""
        state = create_initial_state(mission="Test")

        new_state = state.transition_to("arch")

        assert new_state.current_phase == "arch"
        assert state.current_phase == "pm"  # Original unchanged

    def test_mark_failed(self) -> None:
        """Test marking pipeline as failed."""
        state = create_initial_state(mission="Test")

        new_state = state.mark_failed("Critical error occurred")

        assert new_state.current_phase == "failed"
        assert "Critical error occurred" in new_state.errors

    def test_mark_complete(self) -> None:
        """Test marking pipeline as complete."""
        state = create_initial_state(mission="Test")

        new_state = state.mark_complete()

        assert new_state.current_phase == "complete"

    def test_get_total_cost(self) -> None:
        """Test calculating total cost from execution history."""
        state = create_initial_state(mission="Test")
        metrics1 = ExecutionMetrics(estimated_cost_usd=0.01)
        metrics2 = ExecutionMetrics(estimated_cost_usd=0.02)

        state = state.add_execution(metrics1, "agent1")
        state = state.add_execution(metrics2, "agent2")

        assert state.get_total_cost() == pytest.approx(0.03)

    def test_get_total_tokens(self) -> None:
        """Test calculating total tokens from execution history."""
        state = create_initial_state(mission="Test")
        metrics1 = ExecutionMetrics(tokens_input=100, tokens_output=200)
        metrics2 = ExecutionMetrics(tokens_input=50, tokens_output=150)

        state = state.add_execution(metrics1, "agent1")
        state = state.add_execution(metrics2, "agent2")

        assert state.get_total_tokens() == 500  # 100+200+50+150

    def test_has_artifact_with_existing_file(self, tmp_path: Path) -> None:
        """Test has_artifact returns True for existing files."""
        prd_path = tmp_path / "PRD.md"
        prd_path.write_text("# PRD Content")

        state = create_initial_state(mission="Test").with_update(path_prd=prd_path)

        assert state.has_artifact("prd") is True

    def test_has_artifact_with_nonexistent_file(self) -> None:
        """Test has_artifact returns False for non-existent files."""
        state = create_initial_state(mission="Test").with_update(
            path_prd=Path("/nonexistent/PRD.md")
        )

        assert state.has_artifact("prd") is False

    def test_has_artifact_with_none_path(self) -> None:
        """Test has_artifact returns False when path is None."""
        state = create_initial_state(mission="Test")

        assert state.has_artifact("prd") is False
        assert state.has_artifact("tech_spec") is False

    def test_mission_required(self) -> None:
        """Test that mission is required and cannot be empty."""
        with pytest.raises(ValidationError):
            AgentState(mission="")  # Empty string should fail

    def test_updated_at_changes_on_update(self) -> None:
        """Test that updated_at timestamp changes with updates."""
        state = create_initial_state(mission="Test")
        original_updated = state.updated_at

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        new_state = state.with_update(current_phase="arch")

        assert new_state.updated_at > original_updated


class TestExecutionMetrics:
    """Tests for ExecutionMetrics model."""

    def test_default_values(self) -> None:
        """Test default metric values are zero."""
        metrics = ExecutionMetrics()

        assert metrics.tokens_input == 0
        assert metrics.tokens_output == 0
        assert metrics.execution_time_seconds == 0.0
        assert metrics.estimated_cost_usd == 0.0

    def test_total_tokens(self) -> None:
        """Test total_tokens calculation."""
        metrics = ExecutionMetrics(tokens_input=100, tokens_output=200)

        assert metrics.total_tokens() == 300

    def test_immutability(self) -> None:
        """Test that ExecutionMetrics is frozen."""
        metrics = ExecutionMetrics(tokens_input=100)

        with pytest.raises(ValidationError):
            metrics.tokens_input = 200  # type: ignore


class TestBaseAgentAbstract:
    """Tests for BaseAgent abstract class behavior."""

    def test_cannot_instantiate_directly(self) -> None:
        """Test that BaseAgent cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            BaseAgent()  # type: ignore

        assert "abstract" in str(exc_info.value).lower()

    def test_must_implement_profile_name(self) -> None:
        """Test that subclasses must implement profile_name."""

        class IncompleteAgent(BaseAgent):
            @property
            def role_description(self) -> str:
                return "Test"

            def execute(self, state: AgentState) -> AgentState:
                return state

            def validate_output(self, artifact_path: Path) -> bool:
                return True

        with pytest.raises(TypeError) as exc_info:
            IncompleteAgent()  # type: ignore

        assert "profile_name" in str(exc_info.value)

    def test_must_implement_role_description(self) -> None:
        """Test that subclasses must implement role_description."""

        class IncompleteAgent(BaseAgent):
            @property
            def profile_name(self) -> str:
                return "test"

            def execute(self, state: AgentState) -> AgentState:
                return state

            def validate_output(self, artifact_path: Path) -> bool:
                return True

        with pytest.raises(TypeError) as exc_info:
            IncompleteAgent()  # type: ignore

        assert "role_description" in str(exc_info.value)

    def test_must_implement_execute(self) -> None:
        """Test that subclasses must implement execute."""

        class IncompleteAgent(BaseAgent):
            @property
            def profile_name(self) -> str:
                return "test"

            @property
            def role_description(self) -> str:
                return "Test"

            def validate_output(self, artifact_path: Path) -> bool:
                return True

        with pytest.raises(TypeError) as exc_info:
            IncompleteAgent()  # type: ignore

        assert "execute" in str(exc_info.value)

    def test_must_implement_validate_output(self) -> None:
        """Test that subclasses must implement validate_output."""

        class IncompleteAgent(BaseAgent):
            @property
            def profile_name(self) -> str:
                return "test"

            @property
            def role_description(self) -> str:
                return "Test"

            def execute(self, state: AgentState) -> AgentState:
                return state

        with pytest.raises(TypeError) as exc_info:
            IncompleteAgent()  # type: ignore

        assert "validate_output" in str(exc_info.value)


class TestMockAgent:
    """Tests for MockAgent implementation."""

    def test_can_instantiate(self) -> None:
        """Test that MockAgent can be instantiated."""
        agent = MockAgent()

        assert agent.profile_name == "test"
        assert agent.role_description == "Test agent"

    def test_custom_profile_and_description(self) -> None:
        """Test MockAgent with custom profile and description."""
        agent = MockAgent(profile="custom", description="Custom agent")

        assert agent.profile_name == "custom"
        assert agent.role_description == "Custom agent"

    def test_execute_returns_updated_state(self) -> None:
        """Test that MockAgent.execute returns state with execution recorded."""
        agent = MockAgent()
        state = create_initial_state(mission="Test")

        new_state = agent.execute(state)

        assert len(new_state.execution_history) == 1
        assert new_state.execution_history[0]["agent"] == "test"

    def test_execute_preserves_immutability(self) -> None:
        """Test that execute doesn't mutate original state."""
        agent = MockAgent()
        original = create_initial_state(mission="Test")

        new_state = agent.execute(original)

        assert len(original.execution_history) == 0
        assert len(new_state.execution_history) == 1

    def test_validate_output_checks_existence(self, tmp_path: Path) -> None:
        """Test validate_output returns True for existing files."""
        agent = MockAgent()
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        assert agent.validate_output(test_file) is True

    def test_validate_output_nonexistent_file(self, tmp_path: Path) -> None:
        """Test validate_output returns False for non-existent files."""
        agent = MockAgent()
        nonexistent = tmp_path / "nonexistent.txt"

        assert agent.validate_output(nonexistent) is False


class TestSystemPromptLoading:
    """Tests for system prompt loading functionality."""

    def test_get_system_prompt_file_not_found(self) -> None:
        """Test that missing prompt file raises PromptLoadError."""
        agent = MockAgent(profile="nonexistent")

        with pytest.raises(PromptLoadError) as exc_info:
            agent.get_system_prompt()

        assert "not found" in str(exc_info.value)

    def test_get_system_prompt_loads_from_file(self, tmp_path: Path) -> None:
        """Test successful prompt loading from file."""
        # Create a temporary prompt file
        prompt_content = "# Test Prompt\nYou are a test agent.\n"
        prompt_dir = tmp_path / "personas"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "test_prompt.md"
        prompt_file.write_text(prompt_content)

        agent = MockAgent(profile="test")

        # Patch the PERSONAS_DIR
        with patch.object(BaseAgent, "PERSONAS_DIR", prompt_dir):
            result = agent.get_system_prompt()

        assert result == prompt_content

    def test_prompt_state_injection(self, tmp_path: Path) -> None:
        """Test that state values are injected into prompt template."""
        prompt_content = "Mission: {user_mission}\nProject: {project_name}\n"
        prompt_dir = tmp_path / "personas"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "test_prompt.md"
        prompt_file.write_text(prompt_content)

        agent = MockAgent(profile="test")
        state = create_initial_state(
            mission="Build a web app",
            project_name="WebApp",
        )

        with patch.object(BaseAgent, "PERSONAS_DIR", prompt_dir):
            result = agent.get_system_prompt(state)

        assert "Build a web app" in result
        assert "WebApp" in result
        assert "{user_mission}" not in result
        assert "{project_name}" not in result

    def test_prompt_prd_content_injection(self, tmp_path: Path) -> None:
        """Test PRD content injection into prompt."""
        prompt_content = "PRD:\n{prd_content}\n"
        prompt_dir = tmp_path / "personas"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "test_prompt.md"
        prompt_file.write_text(prompt_content)

        # Create PRD file
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# Product Requirements\n- Feature 1\n- Feature 2")

        agent = MockAgent(profile="test")
        state = create_initial_state(mission="Test").with_update(path_prd=prd_file)

        with patch.object(BaseAgent, "PERSONAS_DIR", prompt_dir):
            result = agent.get_system_prompt(state)

        assert "Feature 1" in result
        assert "Feature 2" in result


class TestArtifactValidation:
    """Tests for artifact validation functionality."""

    def test_validate_required_artifacts_success(self, tmp_path: Path) -> None:
        """Test validation passes when required artifacts exist."""
        prd_file = tmp_path / "PRD.md"
        prd_file.write_text("# PRD")

        spec_file = tmp_path / "TECH_SPEC.md"
        spec_file.write_text("# Tech Spec")

        state = create_initial_state(mission="Test").with_update(
            path_prd=prd_file,
            path_tech_spec=spec_file,
        )

        agent = MockAgent()
        result = agent.validate_required_artifacts(state, ["prd", "tech_spec"])

        assert result is True

    def test_validate_required_artifacts_missing(self, tmp_path: Path) -> None:
        """Test validation fails when required artifacts are missing."""
        state = create_initial_state(mission="Test")

        agent = MockAgent()

        with pytest.raises(ArtifactValidationError) as exc_info:
            agent.validate_required_artifacts(state, ["prd"])

        assert "prd" in str(exc_info.value)

    def test_validate_required_artifacts_file_deleted(self, tmp_path: Path) -> None:
        """Test validation fails when artifact file doesn't exist."""
        prd_file = tmp_path / "PRD.md"  # Don't create the file

        state = create_initial_state(mission="Test").with_update(path_prd=prd_file)

        agent = MockAgent()

        with pytest.raises(ArtifactValidationError):
            agent.validate_required_artifacts(state, ["prd"])


class TestStateImmutabilityValidation:
    """Tests for state immutability validation."""

    def test_warns_when_same_state_returned(self) -> None:
        """Test that returning the same state object triggers warning."""
        agent = MockAgent()
        state = create_initial_state(mission="Test")

        # _validate_state_immutability should return False if same object
        result = agent._validate_state_immutability(state, state)

        assert result is False

    def test_passes_when_new_state_returned(self) -> None:
        """Test that returning a new state passes validation."""
        agent = MockAgent()
        original = create_initial_state(mission="Test")
        new_state = original.with_update(current_phase="arch")

        result = agent._validate_state_immutability(original, new_state)

        assert result is True


class TestAgentInfo:
    """Tests for agent info and representation."""

    def test_get_agent_info(self) -> None:
        """Test get_agent_info returns expected structure."""
        agent = MockAgent(profile="pm", description="Product Manager")

        info = agent.get_agent_info()

        assert info["profile_name"] == "pm"
        assert info["role_description"] == "Product Manager"
        assert "timeout" in info
        assert "log_dir" in info

    def test_repr(self) -> None:
        """Test string representation."""
        agent = MockAgent(profile="pm")

        repr_str = repr(agent)

        assert "MockAgent" in repr_str
        assert "pm" in repr_str


class TestExecutionMetricsCalculation:
    """Tests for metrics calculation from execution results."""

    def test_calculate_metrics_from_result(self) -> None:
        """Test metrics calculation from ExecutionResult."""
        from src.wrappers.claude_wrapper import ExecutionResult

        agent = MockAgent()
        result = ExecutionResult(
            success=True,
            stdout="This is some output text from the execution",
            stderr="",
            exit_code=0,
            execution_time=2.5,
        )

        metrics = agent._calculate_metrics(result)

        assert metrics.execution_time_seconds == 2.5
        assert metrics.tokens_output > 0
        assert metrics.estimated_cost_usd > 0


class TestAcceptanceCriteriaExtraction:
    """Tests for acceptance criteria extraction from PRD."""

    def test_extract_acceptance_criteria_standard_format(self) -> None:
        """Test extraction from standard PRD format."""
        agent = MockAgent()
        prd_content = """
# PRD

## User Stories
- As a user, I want to login

## Functional Requirements
- The system shall authenticate users

## Non-Functional Requirements
- Response time < 200ms

## Acceptance Criteria
- Given valid credentials, when user logs in, then show dashboard
- Given invalid credentials, when user logs in, then show error

## Additional Notes
- None
"""

        criteria = agent._extract_acceptance_criteria(prd_content)

        assert "Given valid credentials" in criteria
        assert "Given invalid credentials" in criteria

    def test_extract_acceptance_criteria_not_found(self) -> None:
        """Test extraction when section not found."""
        agent = MockAgent()
        prd_content = "# PRD\nJust some content without acceptance criteria"

        criteria = agent._extract_acceptance_criteria(prd_content)

        assert "not found" in criteria.lower()


class TestRulesOfEngagementExtraction:
    """Tests for Rules of Engagement extraction from tech spec."""

    def test_extract_rules_standard_format(self) -> None:
        """Test extraction from standard tech spec format."""
        agent = MockAgent()
        spec_content = """
# Technical Specification

## Architecture Overview
Some architecture details

## Rules of Engagement
- Use Pytest for testing
- Maintain 80% code coverage
- No global variables

## Dependencies
- Python 3.10+
"""

        rules = agent._extract_rules_of_engagement(spec_content)

        assert "Pytest" in rules
        assert "80% code coverage" in rules

    def test_extract_rules_not_found(self) -> None:
        """Test extraction when section not found."""
        agent = MockAgent()
        spec_content = "# Tech Spec\nNo rules section here"

        rules = agent._extract_rules_of_engagement(spec_content)

        assert "not found" in rules.lower()
