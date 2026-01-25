"""LangGraph Workflow Definition for Multi-Agent Orchestration.

This module implements the LangGraph state machine for the Waterfall pipeline,
defining nodes for each agent persona and conditional edges per the blueprint.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.orchestration.context_manager import ContextManager
from src.orchestration.state import (
    AgentState,
    StateManager,
    StateValidator,
)

if TYPE_CHECKING:
    from src.wrappers.architect_agent import ArchitectAgent
    from src.wrappers.base_agent import BaseAgent
    from src.wrappers.engineer_agent import EngineerAgent
    from src.wrappers.pm_agent import PMAgent
    from src.wrappers.qa_agent import QAAgent
    from src.wrappers.state import AgentState as WrapperAgentState

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Base exception for workflow errors."""

    pass


class NodeExecutionError(WorkflowError):
    """Raised when a node execution fails."""

    pass


def _convert_to_wrapper_state(state: AgentState) -> "WrapperAgentState":
    """Convert LangGraph state to wrapper AgentState.

    Args:
        state: The LangGraph TypedDict state.

    Returns:
        A Pydantic AgentState for use with agent wrappers.
    """
    from src.wrappers.state import AgentState as WrapperAgentState

    return WrapperAgentState(
        mission=state.get("user_mission", ""),
        project_name=state.get("project_name", "project"),
        work_dir=Path(state.get("work_dir", ".")),
        current_phase=state.get("current_phase", "pm"),
        path_prd=Path(state["path_prd"]) if state.get("path_prd") else None,
        path_tech_spec=Path(state["path_tech_spec"]) if state.get("path_tech_spec") else None,
        path_scaffold_script=Path(state["path_scaffold_script"]) if state.get("path_scaffold_script") else None,
        path_bug_report=Path(state["path_bug_report"]) if state.get("path_bug_report") else None,
        files_created=tuple(Path(f) for f in state.get("files_created", [])),
        qa_passed=state.get("qa_passed"),
        errors=tuple(state.get("errors", [])),
    )


def _convert_from_wrapper_state(
    wrapper_state: "WrapperAgentState",
    original_state: AgentState,
) -> AgentState:
    """Convert wrapper AgentState back to LangGraph state.

    Args:
        wrapper_state: The Pydantic AgentState from agent execution.
        original_state: The original LangGraph state to update.

    Returns:
        Updated LangGraph AgentState.
    """
    updates: dict[str, Any] = {
        "current_phase": wrapper_state.current_phase,
        "qa_passed": wrapper_state.qa_passed if wrapper_state.qa_passed is not None else original_state.get("qa_passed", False),
        "files_created": [str(f) for f in wrapper_state.files_created],
        "errors": list(wrapper_state.errors),
    }

    if wrapper_state.path_prd:
        updates["path_prd"] = str(wrapper_state.path_prd)
    if wrapper_state.path_tech_spec:
        updates["path_tech_spec"] = str(wrapper_state.path_tech_spec)
    if wrapper_state.path_scaffold_script:
        updates["path_scaffold_script"] = str(wrapper_state.path_scaffold_script)
    if wrapper_state.path_bug_report:
        updates["path_bug_report"] = str(wrapper_state.path_bug_report)

    return StateManager.update_state(original_state, updates)


class WorkflowNodes:
    """Container for workflow node implementations.

    This class holds references to agent instances and context manager,
    providing node functions for the LangGraph workflow.
    """

    def __init__(
        self,
        context_manager: ContextManager | None = None,
        pm_agent: "PMAgent | None" = None,
        architect_agent: "ArchitectAgent | None" = None,
        engineer_agent: "EngineerAgent | None" = None,
        qa_agent: "QAAgent | None" = None,
    ) -> None:
        """Initialize workflow nodes.

        Args:
            context_manager: ContextManager for CLAUDE.md generation.
            pm_agent: Product Manager agent instance.
            architect_agent: Architect agent instance.
            engineer_agent: Engineer agent instance.
            qa_agent: QA agent instance.
        """
        self.context_manager = context_manager or ContextManager()
        self._pm_agent = pm_agent
        self._architect_agent = architect_agent
        self._engineer_agent = engineer_agent
        self._qa_agent = qa_agent

    def _get_pm_agent(self) -> "PMAgent":
        """Get or create PM agent."""
        if self._pm_agent is None:
            from src.wrappers.pm_agent import PMAgent
            self._pm_agent = PMAgent()
        return self._pm_agent

    def _get_architect_agent(self) -> "ArchitectAgent":
        """Get or create Architect agent."""
        if self._architect_agent is None:
            from src.wrappers.architect_agent import ArchitectAgent
            self._architect_agent = ArchitectAgent()
        return self._architect_agent

    def _get_engineer_agent(self) -> "EngineerAgent":
        """Get or create Engineer agent."""
        if self._engineer_agent is None:
            from src.wrappers.engineer_agent import EngineerAgent
            self._engineer_agent = EngineerAgent()
        return self._engineer_agent

    def _get_qa_agent(self) -> "QAAgent":
        """Get or create QA agent."""
        if self._qa_agent is None:
            from src.wrappers.qa_agent import QAAgent
            self._qa_agent = QAAgent()
        return self._qa_agent

    def pm_node(self, state: AgentState) -> AgentState:
        """Product Manager node - generates PRD.

        Args:
            state: Current workflow state.

        Returns:
            Updated state with PRD path.
        """
        logger.info("Executing PM node")

        # Update context for PM phase
        self.context_manager.update_context("pm", {
            "mission": state.get("user_mission", ""),
            "metadata": {"project_name": state.get("project_name", "project")},
        })

        # Generate CLAUDE.md
        work_dir = Path(state.get("work_dir", "."))
        self.context_manager.generate_claude_md(work_dir)

        # Execute PM agent
        wrapper_state = _convert_to_wrapper_state(state)
        agent = self._get_pm_agent()

        try:
            result_state = agent.execute(wrapper_state)
            new_state = _convert_from_wrapper_state(result_state, state)
            return StateManager.update_state(new_state, {"current_phase": "arch"})
        except Exception as e:
            logger.error(f"PM node failed: {e}")
            return StateManager.update_state(
                state,
                {
                    "current_phase": "failed",
                    "errors": list(state.get("errors", [])) + [str(e)],
                },
            )

    def architect_node(self, state: AgentState) -> AgentState:
        """Architect node - generates technical specification.

        Args:
            state: Current workflow state.

        Returns:
            Updated state with tech spec path.
        """
        logger.info("Executing Architect node")

        # Update context for Architect phase with PRD reference
        self.context_manager.update_context("arch", {
            "mission": state.get("user_mission", ""),
            "artifacts": [f"PRD: {state.get('path_prd', 'docs/PRD.md')}"],
            "metadata": {"project_name": state.get("project_name", "project")},
        })

        # Generate CLAUDE.md
        work_dir = Path(state.get("work_dir", "."))
        self.context_manager.generate_claude_md(work_dir)

        # Execute Architect agent
        wrapper_state = _convert_to_wrapper_state(state)
        agent = self._get_architect_agent()

        try:
            result_state = agent.execute(wrapper_state)
            new_state = _convert_from_wrapper_state(result_state, state)
            return StateManager.update_state(new_state, {"current_phase": "human_gate"})
        except Exception as e:
            logger.error(f"Architect node failed: {e}")
            return StateManager.update_state(
                state,
                {
                    "current_phase": "failed",
                    "errors": list(state.get("errors", [])) + [str(e)],
                },
            )

    def human_gate_node(self, state: AgentState) -> AgentState:
        """Human gate node - pauses for human approval.

        This node triggers an interrupt. Execution pauses here until
        human approval/rejection is provided via the orchestrator.

        Args:
            state: Current workflow state.

        Returns:
            State unchanged (interrupt will pause execution).
        """
        logger.info("Reached human gate - awaiting approval")
        # This node just returns the state; the interrupt happens at the edge
        return state

    def engineer_node(self, state: AgentState) -> AgentState:
        """Engineer node - implements the code.

        Args:
            state: Current workflow state.

        Returns:
            Updated state with implementation files.
        """
        logger.info("Executing Engineer node")

        # Extract rules from tech spec if available
        rules: list[str] = []
        tech_spec_path = state.get("path_tech_spec")
        if tech_spec_path:
            rules = _extract_rules_from_spec(Path(tech_spec_path))

        # Update context for Engineer phase
        self.context_manager.update_context("eng", {
            "mission": state.get("user_mission", ""),
            "artifacts": [
                f"Tech Spec: {tech_spec_path or 'docs/TECH_SPEC.md'}",
            ],
            "rules": rules,
            "metadata": {"project_name": state.get("project_name", "project")},
        })

        # Generate CLAUDE.md
        work_dir = Path(state.get("work_dir", "."))
        self.context_manager.generate_claude_md(work_dir)

        # Execute Engineer agent
        wrapper_state = _convert_to_wrapper_state(state)
        agent = self._get_engineer_agent()

        try:
            result_state = agent.execute(wrapper_state)
            new_state = _convert_from_wrapper_state(result_state, state)
            return StateManager.update_state(new_state, {"current_phase": "qa"})
        except Exception as e:
            logger.error(f"Engineer node failed: {e}")
            return StateManager.update_state(
                state,
                {
                    "current_phase": "failed",
                    "errors": list(state.get("errors", [])) + [str(e)],
                },
            )

    def qa_node(self, state: AgentState) -> AgentState:
        """QA node - runs tests and validates implementation.

        Args:
            state: Current workflow state.

        Returns:
            Updated state with QA results.
        """
        logger.info("Executing QA node")

        # Update context for QA phase
        self.context_manager.update_context("qa", {
            "mission": state.get("user_mission", ""),
            "artifacts": [
                f"PRD: {state.get('path_prd', 'docs/PRD.md')}",
                f"Tech Spec: {state.get('path_tech_spec', 'docs/TECH_SPEC.md')}",
                "Implementation: src/",
            ],
            "metadata": {"project_name": state.get("project_name", "project")},
        })

        # Generate CLAUDE.md
        work_dir = Path(state.get("work_dir", "."))
        self.context_manager.generate_claude_md(work_dir)

        # Execute QA agent
        wrapper_state = _convert_to_wrapper_state(state)
        agent = self._get_qa_agent()

        try:
            result_state = agent.execute(wrapper_state)
            new_state = _convert_from_wrapper_state(result_state, state)
            # The qa_passed flag is set by the agent
            return new_state
        except Exception as e:
            logger.error(f"QA node failed: {e}")
            return StateManager.update_state(
                state,
                {
                    "current_phase": "failed",
                    "qa_passed": False,
                    "errors": list(state.get("errors", [])) + [str(e)],
                },
            )

    def human_help_node(self, state: AgentState) -> AgentState:
        """Human help node - escalates when max iterations exceeded.

        Args:
            state: Current workflow state.

        Returns:
            State marked for human intervention.
        """
        logger.warning(
            f"Max iterations ({state.get('max_iterations', 5)}) exceeded. "
            "Escalating to human help."
        )
        return state


def _extract_rules_from_spec(spec_path: Path) -> list[str]:
    """Extract Rules of Engagement from technical specification.

    Args:
        spec_path: Path to the technical specification file.

    Returns:
        List of rules extracted from the spec.
    """
    rules: list[str] = []

    if not spec_path.exists():
        return rules

    try:
        content = spec_path.read_text(encoding="utf-8")

        # Find Rules of Engagement section
        import re
        rules_match = re.search(
            r"##\s*Rules\s+of\s+Engagement\s*\n(.*?)(?=\n##|\Z)",
            content,
            re.IGNORECASE | re.DOTALL,
        )

        if rules_match:
            rules_text = rules_match.group(1)
            # Extract bullet points
            for line in rules_text.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    rule = line.lstrip("-* ").strip()
                    if rule:
                        rules.append(rule)
    except Exception as e:
        logger.warning(f"Failed to extract rules from spec: {e}")

    return rules


def route_after_human_gate(state: AgentState) -> Literal["engineer", "architect", "pm", "human_gate", "failed"]:
    """Route after human gate based on decision.

    Args:
        state: Current workflow state.

    Returns:
        The next node name.
    """
    decision = state.get("decision")

    if decision == "APPROVE":
        logger.info("Human approved - proceeding to engineer")
        return "engineer"
    elif decision == "REJECT":
        reject_phase = state.get("reject_phase", "architect")
        logger.info(f"Human rejected - returning to {reject_phase}")
        if reject_phase == "pm":
            return "pm"
        elif reject_phase == "architect":
            return "architect"
        else:
            return "architect"  # Default to architect
    else:
        # No decision yet - stay at gate (interrupt should prevent this)
        logger.warning("No decision provided at human gate")
        return "human_gate"


def route_after_qa(state: AgentState) -> Literal["end", "engineer", "human_help"]:
    """Route after QA based on test results.

    Args:
        state: Current workflow state.

    Returns:
        The next node name or END.
    """
    qa_passed = state.get("qa_passed", False)
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 5)

    if qa_passed:
        logger.info("QA passed - completing workflow")
        return "end"
    elif iteration_count < max_iterations:
        logger.info(f"QA failed - repair loop iteration {iteration_count + 1}/{max_iterations}")
        return "engineer"
    else:
        logger.warning(f"Max iterations ({max_iterations}) reached - escalating to human help")
        return "human_help"


def build_workflow(
    nodes: WorkflowNodes | None = None,
    checkpointer: MemorySaver | None = None,
) -> StateGraph:
    """Build the LangGraph workflow for multi-agent orchestration.

    Args:
        nodes: WorkflowNodes instance with agent references.
        checkpointer: Checkpointer for state persistence.

    Returns:
        Compiled StateGraph ready for execution.
    """
    if nodes is None:
        nodes = WorkflowNodes()

    # Create the state graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("pm", nodes.pm_node)
    graph.add_node("architect", nodes.architect_node)
    graph.add_node("human_gate", nodes.human_gate_node)
    graph.add_node("engineer", nodes.engineer_node)
    graph.add_node("qa", nodes.qa_node)
    graph.add_node("human_help", nodes.human_help_node)

    # Add edges
    # Start -> PM
    graph.add_edge(START, "pm")

    # PM -> Architect
    graph.add_edge("pm", "architect")

    # Architect -> Human Gate
    graph.add_edge("architect", "human_gate")

    # Human Gate -> conditional routing
    graph.add_conditional_edges(
        "human_gate",
        route_after_human_gate,
        {
            "engineer": "engineer",
            "architect": "architect",
            "pm": "pm",
            "human_gate": "human_gate",
            "failed": END,
        },
    )

    # Engineer -> QA
    graph.add_edge("engineer", "qa")

    # QA -> conditional routing
    graph.add_conditional_edges(
        "qa",
        route_after_qa,
        {
            "end": END,
            "engineer": "engineer",
            "human_help": "human_help",
        },
    )

    # Human Help -> END (for now; could be extended)
    graph.add_edge("human_help", END)

    # Compile with checkpointer and interrupt configuration
    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_after=["human_gate"],  # Interrupt after human_gate to await approval
    )


def get_workflow_mermaid() -> str:
    """Generate Mermaid diagram for the workflow.

    Returns:
        Mermaid diagram string.
    """
    mermaid = """```mermaid
stateDiagram-v2
    [*] --> PM
    PM --> Architect
    Architect --> HumanGate

    HumanGate --> Engineer: APPROVE
    HumanGate --> Architect: REJECT (arch)
    HumanGate --> PM: REJECT (prd)

    Engineer --> QA

    QA --> [*]: qa_passed = true
    QA --> Engineer: qa_passed = false & iterations < max
    QA --> HumanHelp: iterations >= max

    HumanHelp --> [*]

    note right of HumanGate
        Interrupt point
        Awaits human approval
    end note

    note right of QA
        Repair loop with
        max 5 iterations
    end note
```"""
    return mermaid


def generate_workflow_diagram(output_path: Path | None = None) -> str:
    """Generate and optionally save workflow diagram.

    Args:
        output_path: Optional path to save the diagram.

    Returns:
        The Mermaid diagram string.
    """
    diagram = get_workflow_mermaid()

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(diagram, encoding="utf-8")
        logger.info(f"Workflow diagram saved to {output_path}")

    return diagram


# Workflow state type for external use
WorkflowState = AgentState
