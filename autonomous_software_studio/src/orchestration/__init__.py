"""LangGraph orchestration control plane.

This package provides the orchestration layer for the multi-agent pipeline,
including state management, workflow definition, and session orchestration.

Modules:
    state: LangGraph state schema and state management utilities.
    workflow: LangGraph workflow definition with nodes and edges.
    orchestrator: Main orchestrator for managing execution lifecycle.
    context_manager: Dynamic CLAUDE.md generation for agents.
"""

from src.orchestration.context_manager import (
    ContextError,
    ContextManager,
    ContextSizeExceededError,
    PhaseContext,
)
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
from src.orchestration.state import (
    AgentState,
    ExecutionLogEntry,
    ExecutionResult,
    StateManager,
    StateTransitionError,
    StateValidationError,
    StateValidator,
    PHASE_ARTIFACTS,
    VALID_TRANSITIONS,
    generate_session_id,
)
from src.orchestration.workflow import (
    NodeExecutionError,
    WorkflowError,
    WorkflowNodes,
    WorkflowState,
    build_workflow,
    generate_workflow_diagram,
    get_workflow_mermaid,
    route_after_human_gate,
    route_after_qa,
)

__all__ = [
    # State
    "AgentState",
    "ExecutionLogEntry",
    "ExecutionResult",
    "StateManager",
    "StateTransitionError",
    "StateValidationError",
    "StateValidator",
    "PHASE_ARTIFACTS",
    "VALID_TRANSITIONS",
    "generate_session_id",
    # Workflow
    "NodeExecutionError",
    "WorkflowError",
    "WorkflowNodes",
    "WorkflowState",
    "build_workflow",
    "generate_workflow_diagram",
    "get_workflow_mermaid",
    "route_after_human_gate",
    "route_after_qa",
    # Orchestrator
    "InvalidOperationError",
    "Orchestrator",
    "OrchestratorConfig",
    "OrchestratorError",
    "SessionExpiredError",
    "SessionInfo",
    "SessionNotFoundError",
    "SessionStatus",
    "SessionStore",
    # Context Manager
    "ContextError",
    "ContextManager",
    "ContextSizeExceededError",
    "PhaseContext",
]
