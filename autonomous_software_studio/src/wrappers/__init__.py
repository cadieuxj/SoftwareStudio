"""Claude CLI wrapper classes and agent implementations.

This package provides:
- ClaudeCLIWrapper: Wrapper for programmatic Claude CLI control
- EnvironmentManager: Multi-account identity management
- BaseAgent: Abstract base class for all agent personas
- PMAgent: Product Manager agent for PRD generation
- ArchitectAgent: Software Architect agent for technical specifications
- EngineerAgent: Senior Engineer agent for code implementation
- QAAgent: QA Engineer agent for testing and bug reports
- AgentState: Immutable state model for pipeline execution
"""

from src.wrappers.base_agent import (
    AgentError,
    ArtifactValidationError,
    BaseAgent,
    MockAgent,
    PromptLoadError,
    StateValidationError,
)
from src.wrappers.claude_wrapper import (
    ClaudeCLIWrapper,
    ClaudeNotFoundError,
    ExecutionError,
    ExecutionResult,
    ExecutionTimeoutError,
)
from src.wrappers.env_manager import (
    ConfigurationError,
    EnvironmentConfig,
    EnvironmentManager,
    InvalidAPIKeyError,
    ProfileNotFoundError,
)
from src.wrappers.state import (
    AgentState,
    ExecutionMetrics,
    create_initial_state,
)

# Import agents (may fail if dependencies not available)
try:
    from src.wrappers.pm_agent import PMAgent, PRDValidationError
    from src.wrappers.architect_agent import (
        ArchitectAgent,
        ScaffoldValidationError,
        TechSpecValidationError,
    )
    from src.wrappers.engineer_agent import (
        BatchExecutionError,
        CodeValidationError,
        EngineerAgent,
        ImplementationBatch,
    )
    from src.wrappers.qa_agent import (
        BugReportValidationError,
        QAAgent,
        TestExecutionError,
        TestResult,
        TestSummary,
    )
except ImportError:
    # Agents may not be available in minimal installations
    pass

__all__ = [
    # Base classes
    "BaseAgent",
    "MockAgent",
    # Agent implementations
    "PMAgent",
    "ArchitectAgent",
    "EngineerAgent",
    "QAAgent",
    # State management
    "AgentState",
    "ExecutionMetrics",
    "create_initial_state",
    # Wrapper classes
    "ClaudeCLIWrapper",
    "ExecutionResult",
    "EnvironmentManager",
    "EnvironmentConfig",
    # Exceptions
    "AgentError",
    "ArtifactValidationError",
    "PromptLoadError",
    "StateValidationError",
    "ClaudeNotFoundError",
    "ExecutionError",
    "ExecutionTimeoutError",
    "ConfigurationError",
    "InvalidAPIKeyError",
    "ProfileNotFoundError",
    "PRDValidationError",
    "TechSpecValidationError",
    "ScaffoldValidationError",
    "CodeValidationError",
    "BatchExecutionError",
    "BugReportValidationError",
    "TestExecutionError",
    # Data classes
    "ImplementationBatch",
    "TestResult",
    "TestSummary",
]
