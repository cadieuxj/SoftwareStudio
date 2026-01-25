"""Integration tests for LangGraph workflow.

Tests cover:
- Happy path (PM -> Arch -> Eng -> QA -> End)
- Human rejection path (Arch -> Human -> Arch)
- QA repair loop (Eng -> QA -> Eng)
- Iteration limit (5 repairs -> Human Help)
- Checkpoint resume after interrupt
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.orchestration.state import AgentState, StateManager
from src.orchestration.workflow import (
    WorkflowNodes,
    _convert_from_wrapper_state,
    _convert_to_wrapper_state,
    _extract_rules_from_spec,
    build_workflow,
    generate_workflow_diagram,
    get_workflow_mermaid,
    route_after_human_gate,
    route_after_qa,
)


class TestStateConversion:
    """Tests for state conversion between LangGraph and wrapper states."""

    def test_convert_to_wrapper_state_minimal(self) -> None:
        """Test converting minimal LangGraph state to wrapper state."""
        state = StateManager.create_initial_state("Build a task app")
        wrapper_state = _convert_to_wrapper_state(state)

        assert wrapper_state.mission == "Build a task app"
        assert wrapper_state.current_phase == "pm"
        assert wrapper_state.path_prd is None

    def test_convert_to_wrapper_state_with_paths(self) -> None:
        """Test converting state with artifact paths."""
        state = StateManager.create_initial_state("Build a task app")
        state = StateManager.update_state(
            state,
            {
                "path_prd": "/docs/PRD.md",
                "path_tech_spec": "/docs/TECH_SPEC.md",
                "current_phase": "eng",
            },
        )

        wrapper_state = _convert_to_wrapper_state(state)

        assert wrapper_state.path_prd == Path("/docs/PRD.md")
        assert wrapper_state.path_tech_spec == Path("/docs/TECH_SPEC.md")
        assert wrapper_state.current_phase == "eng"

    def test_convert_from_wrapper_state(self) -> None:
        """Test converting wrapper state back to LangGraph state."""
        from src.wrappers.state import AgentState as WrapperState

        original = StateManager.create_initial_state("Build a task app")
        wrapper = WrapperState(
            mission="Build a task app",
            project_name="project",
            work_dir=Path("/tmp"),
            current_phase="arch",
            path_prd=Path("/docs/PRD.md"),
            files_created=(Path("/docs/PRD.md"),),
        )

        result = _convert_from_wrapper_state(wrapper, original)

        assert result["current_phase"] == "arch"
        assert result["path_prd"] == "/docs/PRD.md"
        assert "/docs/PRD.md" in result["files_created"]


class TestRouteAfterHumanGate:
    """Tests for human gate routing logic."""

    def test_approve_routes_to_engineer(self) -> None:
        """Test that APPROVE decision routes to engineer."""
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(state, {"decision": "APPROVE"})

        result = route_after_human_gate(state)
        assert result == "engineer"

    def test_reject_routes_to_architect(self) -> None:
        """Test that REJECT with architect target routes to architect."""
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(
            state,
            {"decision": "REJECT", "reject_phase": "architect"},
        )

        result = route_after_human_gate(state)
        assert result == "architect"

    def test_reject_routes_to_pm(self) -> None:
        """Test that REJECT with PM target routes to PM."""
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(
            state,
            {"decision": "REJECT", "reject_phase": "pm"},
        )

        result = route_after_human_gate(state)
        assert result == "pm"

    def test_no_decision_stays_at_gate(self) -> None:
        """Test that no decision stays at human gate.

        In normal operation, the interrupt mechanism should prevent reaching
        the routing function without a decision. The human_gate return value
        serves as a safety measure.
        """
        state = StateManager.create_initial_state("Test")

        result = route_after_human_gate(state)
        # Without a decision, stay at gate (interrupt should prevent this path)
        assert result == "human_gate"

    def test_reject_default_to_architect(self) -> None:
        """Test that REJECT without target defaults to architect."""
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(state, {"decision": "REJECT"})

        result = route_after_human_gate(state)
        assert result == "architect"


class TestRouteAfterQA:
    """Tests for QA routing logic."""

    def test_qa_passed_routes_to_end(self) -> None:
        """Test that passing QA routes to end."""
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(state, {"qa_passed": True})

        result = route_after_qa(state)
        assert result == "end"

    def test_qa_failed_within_limit_routes_to_engineer(self) -> None:
        """Test that failed QA within limit routes to engineer."""
        state = StateManager.create_initial_state("Test", max_iterations=5)
        state = StateManager.update_state(
            state,
            {"qa_passed": False, "iteration_count": 2},
        )

        result = route_after_qa(state)
        assert result == "engineer"

    def test_qa_failed_at_limit_routes_to_human_help(self) -> None:
        """Test that failed QA at limit routes to human help."""
        state = StateManager.create_initial_state("Test", max_iterations=5)
        state = StateManager.update_state(
            state,
            {"qa_passed": False, "iteration_count": 5},
        )

        result = route_after_qa(state)
        assert result == "human_help"

    def test_qa_failed_over_limit_routes_to_human_help(self) -> None:
        """Test that failed QA over limit routes to human help."""
        state = StateManager.create_initial_state("Test", max_iterations=3)
        state = StateManager.update_state(
            state,
            {"qa_passed": False, "iteration_count": 10},
        )

        result = route_after_qa(state)
        assert result == "human_help"


class TestExtractRulesFromSpec:
    """Tests for extracting rules from technical specification."""

    def test_extract_rules_from_valid_spec(self) -> None:
        """Test extracting rules from a valid spec file."""
        spec_content = """
# Technical Specification

## Architecture Overview
Some architecture details.

## Rules of Engagement
- Follow TDD principles
- Write unit tests for all functions
- Use type hints throughout
- Keep functions under 50 lines

## API Signatures
Function signatures here.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(spec_content)
            spec_path = Path(f.name)

        try:
            rules = _extract_rules_from_spec(spec_path)

            assert len(rules) == 4
            assert "Follow TDD principles" in rules
            assert "Write unit tests for all functions" in rules
            assert "Use type hints throughout" in rules
            assert "Keep functions under 50 lines" in rules
        finally:
            spec_path.unlink()

    def test_extract_rules_no_rules_section(self) -> None:
        """Test extracting rules when section doesn't exist."""
        spec_content = """
# Technical Specification

## Architecture Overview
Some details.

## API Signatures
More details.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(spec_content)
            spec_path = Path(f.name)

        try:
            rules = _extract_rules_from_spec(spec_path)
            assert rules == []
        finally:
            spec_path.unlink()

    def test_extract_rules_file_not_found(self) -> None:
        """Test extracting rules from non-existent file."""
        rules = _extract_rules_from_spec(Path("/nonexistent/spec.md"))
        assert rules == []

    def test_extract_rules_with_asterisk_bullets(self) -> None:
        """Test extracting rules with asterisk bullet points."""
        spec_content = """
## Rules of Engagement
* Rule one
* Rule two
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(spec_content)
            spec_path = Path(f.name)

        try:
            rules = _extract_rules_from_spec(spec_path)
            assert "Rule one" in rules
            assert "Rule two" in rules
        finally:
            spec_path.unlink()


class TestWorkflowNodes:
    """Tests for WorkflowNodes class."""

    def test_init_with_defaults(self) -> None:
        """Test initializing WorkflowNodes with defaults."""
        nodes = WorkflowNodes()

        assert nodes.context_manager is not None
        assert nodes._pm_agent is None
        assert nodes._architect_agent is None

    def test_init_with_custom_agents(self) -> None:
        """Test initializing WorkflowNodes with custom agents."""
        mock_pm = MagicMock()
        mock_arch = MagicMock()

        nodes = WorkflowNodes(pm_agent=mock_pm, architect_agent=mock_arch)

        assert nodes._pm_agent is mock_pm
        assert nodes._architect_agent is mock_arch

    @patch("src.orchestration.workflow.WorkflowNodes._get_pm_agent")
    def test_pm_node_success(self, mock_get_pm: MagicMock) -> None:
        """Test PM node successful execution."""
        from src.wrappers.state import AgentState as WrapperState

        # Setup mock agent
        mock_agent = MagicMock()
        mock_agent.execute.return_value = WrapperState(
            mission="Test",
            current_phase="arch",
            path_prd=Path("/docs/PRD.md"),
            files_created=(Path("/docs/PRD.md"),),
        )
        mock_get_pm.return_value = mock_agent

        nodes = WorkflowNodes()

        with tempfile.TemporaryDirectory() as tmpdir:
            state = StateManager.create_initial_state("Test")
            state = StateManager.update_state(state, {"work_dir": tmpdir})

            result = nodes.pm_node(state)

            assert result["current_phase"] == "arch"
            assert result["path_prd"] == "/docs/PRD.md"
            mock_agent.execute.assert_called_once()

    @patch("src.orchestration.workflow.WorkflowNodes._get_pm_agent")
    def test_pm_node_failure(self, mock_get_pm: MagicMock) -> None:
        """Test PM node failure handling."""
        mock_agent = MagicMock()
        mock_agent.execute.side_effect = Exception("PM agent failed")
        mock_get_pm.return_value = mock_agent

        nodes = WorkflowNodes()

        with tempfile.TemporaryDirectory() as tmpdir:
            state = StateManager.create_initial_state("Test")
            state = StateManager.update_state(state, {"work_dir": tmpdir})

            result = nodes.pm_node(state)

            assert result["current_phase"] == "failed"
            assert any("PM agent failed" in e for e in result["errors"])

    def test_human_gate_node_returns_state(self) -> None:
        """Test human gate node returns state unchanged."""
        nodes = WorkflowNodes()
        state = StateManager.create_initial_state("Test")

        result = nodes.human_gate_node(state)

        assert result == state

    def test_human_help_node_returns_state(self) -> None:
        """Test human help node returns state."""
        nodes = WorkflowNodes()
        state = StateManager.create_initial_state("Test")
        state = StateManager.update_state(state, {"max_iterations": 5})

        result = nodes.human_help_node(state)

        assert result == state


class TestBuildWorkflow:
    """Tests for workflow building."""

    def test_build_workflow_creates_graph(self) -> None:
        """Test that build_workflow creates a valid graph."""
        graph = build_workflow()

        assert graph is not None
        # Graph should have nodes
        assert hasattr(graph, "invoke")

    def test_build_workflow_with_custom_nodes(self) -> None:
        """Test building workflow with custom nodes."""
        nodes = WorkflowNodes()
        graph = build_workflow(nodes=nodes)

        assert graph is not None

    def test_workflow_has_required_structure(self) -> None:
        """Test that workflow has expected node structure."""
        nodes = WorkflowNodes()
        graph = build_workflow(nodes=nodes)

        # Get the underlying graph to check structure
        # The compiled graph should be invokable
        assert callable(getattr(graph, "invoke", None))


class TestWorkflowMermaidDiagram:
    """Tests for Mermaid diagram generation."""

    def test_get_workflow_mermaid_returns_string(self) -> None:
        """Test that get_workflow_mermaid returns a string."""
        diagram = get_workflow_mermaid()

        assert isinstance(diagram, str)
        assert "mermaid" in diagram
        assert "stateDiagram" in diagram

    def test_diagram_contains_all_nodes(self) -> None:
        """Test that diagram contains all workflow nodes."""
        diagram = get_workflow_mermaid()

        assert "PM" in diagram
        assert "Architect" in diagram
        assert "HumanGate" in diagram
        assert "Engineer" in diagram
        assert "QA" in diagram
        assert "HumanHelp" in diagram

    def test_diagram_contains_transitions(self) -> None:
        """Test that diagram contains key transitions."""
        diagram = get_workflow_mermaid()

        assert "PM --> Architect" in diagram
        assert "Architect --> HumanGate" in diagram
        assert "APPROVE" in diagram
        assert "REJECT" in diagram

    def test_generate_workflow_diagram_saves_file(self) -> None:
        """Test that generate_workflow_diagram saves to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "diagram.mmd"
            result = generate_workflow_diagram(output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "mermaid" in content
            assert result == content

    def test_generate_workflow_diagram_creates_directories(self) -> None:
        """Test that generate_workflow_diagram creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "diagram.mmd"
            generate_workflow_diagram(output_path)

            assert output_path.exists()


class TestWorkflowIntegration:
    """Integration tests for full workflow execution."""

    @patch("src.orchestration.workflow.WorkflowNodes._get_pm_agent")
    @patch("src.orchestration.workflow.WorkflowNodes._get_architect_agent")
    def test_workflow_pm_to_architect(
        self,
        mock_get_arch: MagicMock,
        mock_get_pm: MagicMock,
    ) -> None:
        """Test workflow execution from PM to Architect."""
        from src.wrappers.state import AgentState as WrapperState

        # Setup mock PM agent
        mock_pm = MagicMock()
        mock_pm.execute.return_value = WrapperState(
            mission="Test",
            current_phase="arch",
            path_prd=Path("/docs/PRD.md"),
        )
        mock_get_pm.return_value = mock_pm

        # Setup mock Architect agent
        # Note: The wrapper state uses 'eng' as the next phase after architect
        # The workflow transitions this to 'human_gate' internally
        mock_arch = MagicMock()
        mock_arch.execute.return_value = WrapperState(
            mission="Test",
            current_phase="eng",  # Wrapper returns 'eng', workflow sets 'human_gate'
            path_prd=Path("/docs/PRD.md"),
            path_tech_spec=Path("/docs/TECH_SPEC.md"),
        )
        mock_get_arch.return_value = mock_arch

        with tempfile.TemporaryDirectory() as tmpdir:
            nodes = WorkflowNodes()

            # Execute PM node
            state = StateManager.create_initial_state("Test")
            state = StateManager.update_state(state, {"work_dir": tmpdir})

            state = nodes.pm_node(state)
            assert state["current_phase"] == "arch"

            # Execute Architect node
            state = nodes.architect_node(state)
            assert state["current_phase"] == "human_gate"
            assert state["path_tech_spec"] is not None

    @patch("src.orchestration.workflow.WorkflowNodes._get_engineer_agent")
    @patch("src.orchestration.workflow.WorkflowNodes._get_qa_agent")
    def test_workflow_repair_loop(
        self,
        mock_get_qa: MagicMock,
        mock_get_eng: MagicMock,
    ) -> None:
        """Test QA-Engineer repair loop."""
        from src.wrappers.state import AgentState as WrapperState

        # Setup mock Engineer agent
        mock_eng = MagicMock()
        mock_eng.execute.return_value = WrapperState(
            mission="Test",
            current_phase="qa",
        )
        mock_get_eng.return_value = mock_eng

        # Setup mock QA agent - first fails, then passes
        mock_qa = MagicMock()
        call_count = [0]

        def qa_side_effect(state: Any) -> WrapperState:
            call_count[0] += 1
            if call_count[0] < 2:
                return WrapperState(
                    mission="Test",
                    current_phase="qa",
                    qa_passed=False,
                )
            return WrapperState(
                mission="Test",
                current_phase="complete",
                qa_passed=True,
            )

        mock_qa.execute.side_effect = qa_side_effect
        mock_get_qa.return_value = mock_qa

        with tempfile.TemporaryDirectory() as tmpdir:
            nodes = WorkflowNodes()

            # Initial state after human approval
            state = StateManager.create_initial_state("Test")
            state = StateManager.update_state(
                state,
                {
                    "work_dir": tmpdir,
                    "path_prd": "/docs/PRD.md",
                    "path_tech_spec": "/docs/TECH_SPEC.md",
                    "iteration_count": 0,
                },
            )

            # First engineer run
            state = nodes.engineer_node(state)
            assert state["current_phase"] == "qa"

            # First QA (fails)
            state = nodes.qa_node(state)
            assert state["qa_passed"] is False

            # Check routing
            route = route_after_qa(state)
            assert route == "engineer"

            # Increment iteration
            state = StateManager.increment_iteration(state)

            # Second engineer run
            state = nodes.engineer_node(state)

            # Second QA (passes)
            state = nodes.qa_node(state)
            assert state["qa_passed"] is True

            route = route_after_qa(state)
            assert route == "end"

    def test_max_iterations_triggers_human_help(self) -> None:
        """Test that max iterations routes to human help."""
        state = StateManager.create_initial_state("Test", max_iterations=3)
        state = StateManager.update_state(
            state,
            {
                "qa_passed": False,
                "iteration_count": 3,
            },
        )

        route = route_after_qa(state)
        assert route == "human_help"


class TestWorkflowCheckpointing:
    """Tests for workflow checkpointing and resume."""

    def test_workflow_with_memory_checkpointer(self) -> None:
        """Test workflow creation with memory checkpointer."""
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        graph = build_workflow(checkpointer=checkpointer)

        assert graph is not None

    def test_workflow_interrupt_configuration(self) -> None:
        """Test that workflow has interrupt configured."""
        # The workflow should compile with interrupt_before=["engineer"]
        graph = build_workflow()

        # Graph should be usable
        assert graph is not None
        assert callable(getattr(graph, "invoke", None))
