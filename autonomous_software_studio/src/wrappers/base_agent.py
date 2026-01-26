"""Base Agent Abstract Class for Multi-Agent Orchestration.

This module defines the abstract base class that all agent personas must inherit from.
It enforces a consistent interface across PM, Architect, Engineer, and QA agents.
"""

from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from src.config.agent_settings import AgentSettingsManager, UsageLimitError
from src.wrappers.claude_wrapper import ClaudeCLIWrapper, ExecutionResult
from src.wrappers.env_manager import EnvironmentManager
from src.wrappers.state import AgentState, ExecutionMetrics


class AgentError(Exception):
    """Base exception for agent-related errors."""

    pass


class PromptLoadError(AgentError):
    """Raised when system prompt cannot be loaded."""

    pass


class ArtifactValidationError(AgentError):
    """Raised when artifact validation fails."""

    pass


class StateValidationError(AgentError):
    """Raised when state validation fails."""

    pass


class ExecutionTimeoutError(AgentError):
    """Raised when agent execution times out."""

    pass


class BaseAgent(ABC):
    """Abstract base class for all agent personas.

    This class defines the interface that all agents must implement and provides
    common functionality for prompt loading, state management, and execution metrics.

    Agents are stateless - they receive state as input and return new state as output.
    No instance variables should store mutable state between executions.

    Class Attributes:
        PERSONAS_DIR: Path to the personas directory containing prompt files.
        DEFAULT_TIMEOUT: Default execution timeout in seconds.

    Example:
        >>> class MyAgent(BaseAgent):
        ...     @property
        ...     def profile_name(self) -> str:
        ...         return "my_agent"
        ...
        ...     @property
        ...     def role_description(self) -> str:
        ...         return "A custom agent"
        ...
        ...     def execute(self, state: AgentState) -> AgentState:
        ...         # Implementation
        ...         return state.with_update(...)
    """

    # Path to personas directory (relative to project root)
    PERSONAS_DIR: ClassVar[Path] = Path(__file__).parent.parent / "personas"

    # Default execution timeout in seconds
    DEFAULT_TIMEOUT: ClassVar[int] = 180

    # Cost estimates per 1K tokens (Claude 3.5 Sonnet pricing as baseline)
    TOKEN_COST_INPUT: ClassVar[float] = 0.003  # $3 per 1M input tokens
    TOKEN_COST_OUTPUT: ClassVar[float] = 0.015  # $15 per 1M output tokens

    def __init__(
        self,
        env_manager: EnvironmentManager | None = None,
        timeout: int | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize the base agent.

        Args:
            env_manager: Environment manager for profile configuration.
                Defaults to a new instance if not provided.
            timeout: Execution timeout in seconds. Defaults to DEFAULT_TIMEOUT.
            log_dir: Directory for logs. Defaults to ./logs.
        """
        self._env_manager = env_manager or EnvironmentManager()
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_dir = log_dir or Path("logs")
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._logger = self._setup_logger()
        self._wrapper: ClaudeCLIWrapper | None = None

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for this agent.

        Returns:
            Configured logger instance.
        """
        logger = logging.getLogger(f"agent.{self.profile_name}")
        logger.setLevel(logging.DEBUG)

        # File handler
        log_file = self._log_dir / f"agent_{self.profile_name}.log"
        if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    @property
    @abstractmethod
    def profile_name(self) -> str:
        """Return the profile name for this agent.

        This is used to load the correct environment configuration and
        system prompt file.

        Returns:
            Profile name (e.g., 'pm', 'arch', 'eng', 'qa').
        """
        pass

    @property
    @abstractmethod
    def role_description(self) -> str:
        """Return a human-readable description of this agent's role.

        Returns:
            Description of the agent's role and responsibilities.
        """
        pass

    @abstractmethod
    def execute(self, state: AgentState) -> AgentState:
        """Execute the agent's task with the given state.

        This method must be implemented by all subclasses. It receives the
        current pipeline state, performs the agent's work, and returns a
        new state with any updates.

        IMPORTANT: This method must NOT mutate the input state. Always use
        state.with_update() or similar methods to create new state.

        Args:
            state: The current pipeline state.

        Returns:
            A new AgentState with updates from this agent's execution.

        Raises:
            AgentError: If execution fails.
            StateValidationError: If state is invalid.
        """
        pass

    @abstractmethod
    def validate_output(self, artifact_path: Path) -> bool:
        """Validate the output artifact created by this agent.

        Each agent type has specific validation rules for its artifacts.

        Args:
            artifact_path: Path to the artifact to validate.

        Returns:
            True if artifact is valid, False otherwise.
        """
        pass

    def get_system_prompt(self, state: AgentState | None = None) -> str:
        """Load and return the system prompt for this agent.

        The prompt is loaded from src/personas/{profile_name}_prompt.md and
        optionally has state values injected into template placeholders.

        Args:
            state: Optional state to inject into prompt template.

        Returns:
            The system prompt string with any placeholders filled.

        Raises:
            PromptLoadError: If prompt file cannot be loaded.
        """
        prompt_path = self.PERSONAS_DIR / f"{self.profile_name}_prompt.md"

        try:
            settings_manager = AgentSettingsManager()
            override_path = settings_manager.get_prompt_path(self.profile_name)
            if override_path and Path(override_path).exists():
                prompt_path = Path(override_path)
        except Exception as e:
            self._logger.warning(f"Prompt override lookup failed: {e}")

        if not prompt_path.exists():
            self._logger.error(f"System prompt not found at: {prompt_path}")
            raise PromptLoadError(
                f"System prompt file not found: {prompt_path}. "
                f"Please create src/personas/{self.profile_name}_prompt.md"
            )

        try:
            prompt_content = prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            self._logger.error(f"Failed to read prompt file: {e}")
            raise PromptLoadError(f"Failed to read prompt file: {e}") from e

        # Inject state values if provided
        if state is not None:
            prompt_content = self._inject_state_into_prompt(prompt_content, state)

        return prompt_content

    def _inject_state_into_prompt(
        self,
        prompt: str,
        state: AgentState,
    ) -> str:
        """Inject state values into prompt template placeholders.

        Placeholders use the format {placeholder_name} and are replaced
        with corresponding values from the state or derived content.

        Args:
            prompt: The prompt template with placeholders.
            state: The state to inject values from.

        Returns:
            The prompt with placeholders replaced.
        """
        replacements: dict[str, str] = {
            "user_mission": state.mission,
            "project_name": state.project_name,
            "work_dir": str(state.work_dir),
            "current_phase": state.current_phase,
        }

        # Add PRD content if available
        if state.path_prd and state.path_prd.exists():
            try:
                replacements["prd_content"] = state.path_prd.read_text(encoding="utf-8")
            except Exception:
                replacements["prd_content"] = "[PRD content unavailable]"
        else:
            replacements["prd_content"] = "[PRD not yet generated]"

        # Add tech spec content if available
        if state.path_tech_spec and state.path_tech_spec.exists():
            try:
                replacements["tech_spec_content"] = state.path_tech_spec.read_text(
                    encoding="utf-8"
                )
            except Exception:
                replacements["tech_spec_content"] = "[Tech spec content unavailable]"
        else:
            replacements["tech_spec_content"] = "[Tech spec not yet generated]"

        # Extract acceptance criteria from PRD if available
        if state.path_prd and state.path_prd.exists():
            try:
                prd_content = state.path_prd.read_text(encoding="utf-8")
                criteria = self._extract_acceptance_criteria(prd_content)
                replacements["acceptance_criteria"] = criteria
            except Exception:
                replacements["acceptance_criteria"] = "[Acceptance criteria unavailable]"
        else:
            replacements["acceptance_criteria"] = "[No acceptance criteria yet]"

        # Extract Rules of Engagement from tech spec if available
        if state.path_tech_spec and state.path_tech_spec.exists():
            try:
                spec_content = state.path_tech_spec.read_text(encoding="utf-8")
                rules = self._extract_rules_of_engagement(spec_content)
                replacements["rules_of_engagement"] = rules
            except Exception:
                replacements["rules_of_engagement"] = "[Rules unavailable]"
        else:
            replacements["rules_of_engagement"] = "[No rules of engagement yet]"

        # Perform replacements
        for key, value in replacements.items():
            placeholder = "{" + key + "}"
            prompt = prompt.replace(placeholder, value)

        return prompt

    def _extract_acceptance_criteria(self, prd_content: str) -> str:
        """Extract acceptance criteria section from PRD.

        Args:
            prd_content: The full PRD document content.

        Returns:
            The acceptance criteria section or a placeholder.
        """
        # Look for acceptance criteria section
        patterns = [
            r"##\s*(?:4\.\s*)?Acceptance Criteria\s*\n(.*?)(?=\n##|\Z)",
            r"##\s*Acceptance Criteria\s*\n(.*?)(?=\n##|\Z)",
            r"\*\*Acceptance Criteria\*\*\s*\n(.*?)(?=\n\*\*|\n##|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, prd_content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "[Acceptance criteria section not found in PRD]"

    def _extract_rules_of_engagement(self, spec_content: str) -> str:
        """Extract Rules of Engagement section from technical spec.

        Args:
            spec_content: The full technical specification content.

        Returns:
            The rules of engagement section or a placeholder.
        """
        patterns = [
            r"##\s*(?:6\.\s*)?Rules of Engagement\s*\n(.*?)(?=\n##|\Z)",
            r"##\s*Rules of Engagement for Engineers\s*\n(.*?)(?=\n##|\Z)",
            r"\*\*Rules of Engagement\*\*\s*\n(.*?)(?=\n\*\*|\n##|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, spec_content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "[Rules of Engagement section not found in tech spec]"

    def validate_required_artifacts(
        self,
        state: AgentState,
        required: list[str],
    ) -> bool:
        """Validate that required artifacts exist before execution.

        Args:
            state: The current state to check.
            required: List of required artifact types.
                Valid values: 'prd', 'tech_spec', 'scaffold'.

        Returns:
            True if all required artifacts exist, False otherwise.

        Raises:
            ArtifactValidationError: If required artifacts are missing.
        """
        artifact_map = {
            "prd": state.path_prd,
            "tech_spec": state.path_tech_spec,
            "scaffold": state.path_scaffold_script,
        }

        missing = []
        for artifact_type in required:
            path = artifact_map.get(artifact_type)
            if path is None or not path.exists():
                missing.append(artifact_type)

        if missing:
            msg = f"Missing required artifacts: {', '.join(missing)}"
            self._logger.error(msg)
            raise ArtifactValidationError(msg)

        return True

    def _get_wrapper(self) -> ClaudeCLIWrapper:
        """Get or create the Claude CLI wrapper for this agent.

        Returns:
            Configured ClaudeCLIWrapper instance.
        """
        if self._wrapper is None:
            self._wrapper = ClaudeCLIWrapper(
                profile_name=self.profile_name,
                env_manager=self._env_manager,
                timeout=self._timeout,
                log_dir=self._log_dir,
            )
        return self._wrapper

    def _execute_claude(
        self,
        prompt: str,
        work_dir: Path,
        verbose: bool = True,
    ) -> ExecutionResult:
        """Execute Claude CLI with the given prompt.

        Args:
            prompt: The prompt to send to Claude.
            work_dir: Working directory for execution.
            verbose: Whether to enable verbose output.

        Returns:
            ExecutionResult with output and status.
        """
        wrapper = self._get_wrapper()
        self._logger.info(f"Executing Claude for {self.profile_name} agent")
        self._logger.debug(f"Work directory: {work_dir}")

        start_time = time.time()
        try:
            settings_manager = AgentSettingsManager()
            warning = settings_manager.check_and_record_usage(self.profile_name, units=1)
            if warning:
                self._logger.warning(warning)
        except UsageLimitError as exc:
            raise AgentError(str(exc)) from exc
        result = wrapper.execute_headless(prompt, work_dir, verbose)
        elapsed = time.time() - start_time

        self._logger.info(
            f"Execution completed: success={result.success}, "
            f"time={elapsed:.2f}s, exit_code={result.exit_code}"
        )

        if not result.success:
            self._logger.error(f"Execution failed: {result.stderr}")

        return result

    def _calculate_metrics(self, result: ExecutionResult) -> ExecutionMetrics:
        """Calculate execution metrics from result.

        Note: Token counts are estimated from output length since Claude CLI
        doesn't provide exact token counts in headless mode.

        Args:
            result: The execution result.

        Returns:
            ExecutionMetrics with estimated values.
        """
        # Estimate tokens from character count (rough: ~4 chars per token)
        output_text = result.get_output()
        tokens_output = len(output_text) // 4

        # Assume input tokens are roughly proportional (this is an estimate)
        tokens_input = tokens_output // 2

        # Calculate estimated cost
        cost = (
            (tokens_input / 1000) * self.TOKEN_COST_INPUT
            + (tokens_output / 1000) * self.TOKEN_COST_OUTPUT
        )

        return ExecutionMetrics(
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            execution_time_seconds=result.execution_time,
            estimated_cost_usd=round(cost, 6),
        )

    def _validate_state_immutability(
        self,
        original: AgentState,
        returned: AgentState,
    ) -> bool:
        """Verify that the original state was not mutated.

        This is a safety check to ensure agents follow the immutability
        contract. It compares the original state to ensure it hasn't changed.

        Args:
            original: The original state passed to execute().
            returned: The state returned from execute().

        Returns:
            True if original state is unchanged.

        Raises:
            StateValidationError: If state was mutated in place.
        """
        # Since AgentState is a frozen Pydantic model, direct mutation
        # would raise an error. This check is more for documentation
        # and catching any workarounds.
        if original is returned:
            self._logger.warning(
                "Agent returned the same state object. "
                "Agents should return a new state via with_update()."
            )
            return False

        return True

    def get_agent_info(self) -> dict[str, Any]:
        """Get information about this agent.

        Returns:
            Dictionary with agent configuration details.
        """
        return {
            "profile_name": self.profile_name,
            "role_description": self.role_description,
            "timeout": self._timeout,
            "log_dir": str(self._log_dir),
            "personas_dir": str(self.PERSONAS_DIR),
            "prompt_file": str(self.PERSONAS_DIR / f"{self.profile_name}_prompt.md"),
        }

    def __repr__(self) -> str:
        """Return string representation of the agent."""
        return f"{self.__class__.__name__}(profile={self.profile_name})"


class MockAgent(BaseAgent):
    """Mock agent implementation for testing purposes.

    This agent can be used in tests to verify the base class behavior
    without requiring actual Claude CLI execution.
    """

    def __init__(
        self,
        profile: str = "test",
        description: str = "Test agent",
        **kwargs: Any,
    ) -> None:
        """Initialize mock agent.

        Args:
            profile: Profile name to use.
            description: Role description.
            **kwargs: Additional arguments passed to BaseAgent.
        """
        self._profile = profile
        self._description = description
        super().__init__(**kwargs)

    @property
    def profile_name(self) -> str:
        """Return the mock profile name."""
        return self._profile

    @property
    def role_description(self) -> str:
        """Return the mock role description."""
        return self._description

    def execute(self, state: AgentState) -> AgentState:
        """Execute mock agent - just returns updated state.

        Args:
            state: Current state.

        Returns:
            Updated state with mock execution recorded.
        """
        metrics = ExecutionMetrics(
            tokens_input=100,
            tokens_output=200,
            execution_time_seconds=1.0,
            estimated_cost_usd=0.001,
        )
        return state.add_execution(metrics, self.profile_name)

    def validate_output(self, artifact_path: Path) -> bool:
        """Validate mock output - always returns True.

        Args:
            artifact_path: Path to validate.

        Returns:
            Always True for mock.
        """
        return artifact_path.exists()
