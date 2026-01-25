"""Agent State Management with Pydantic Models.

This module defines the AgentState model for tracking state across
the multi-agent orchestration pipeline. State is immutable to ensure
consistency and predictability in the waterfall workflow.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExecutionMetrics(BaseModel):
    """Metrics captured during agent execution.

    Attributes:
        tokens_input: Number of input tokens consumed.
        tokens_output: Number of output tokens generated.
        execution_time_seconds: Time taken for execution.
        estimated_cost_usd: Estimated cost in USD.
    """

    model_config = ConfigDict(frozen=True)

    tokens_input: int = 0
    tokens_output: int = 0
    execution_time_seconds: float = 0.0
    estimated_cost_usd: float = 0.0

    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.tokens_input + self.tokens_output


class AgentState(BaseModel):
    """Immutable state object passed between agents in the pipeline.

    This model enforces immutability - any state changes must create a new
    instance rather than mutating the existing one. This ensures clean
    handoffs between pipeline stages.

    Attributes:
        mission: The user's original mission/request.
        project_name: Name of the project being built.
        work_dir: Working directory for the project.
        current_phase: Current pipeline phase (pm, arch, eng, qa).
        path_prd: Path to the PRD document (set by PM agent).
        path_tech_spec: Path to the technical spec (set by Architect).
        path_scaffold_script: Path to scaffold.sh (set by Architect).
        path_bug_report: Path to bug report (set by QA if tests fail).
        files_created: List of files created by agents.
        qa_passed: Whether QA tests passed.
        errors: List of errors encountered during execution.
        metadata: Additional key-value metadata.
        execution_history: History of agent executions with metrics.
        created_at: Timestamp when state was created.
        updated_at: Timestamp when state was last updated.
    """

    model_config = ConfigDict(frozen=True)

    # Core mission
    mission: str = Field(
        ...,
        min_length=1,
        description="The user's original mission/request"
    )
    project_name: str = Field(
        default="project",
        description="Name of the project being built"
    )
    work_dir: Path = Field(
        default_factory=Path.cwd,
        description="Working directory for the project"
    )

    # Pipeline tracking
    current_phase: str = Field(
        default="pm",
        description="Current pipeline phase (pm, arch, eng, qa)"
    )

    # Artifact paths (set by respective agents)
    path_prd: Path | None = Field(
        default=None,
        description="Path to PRD document"
    )
    path_tech_spec: Path | None = Field(
        default=None,
        description="Path to technical specification"
    )
    path_scaffold_script: Path | None = Field(
        default=None,
        description="Path to scaffold.sh script"
    )
    path_bug_report: Path | None = Field(
        default=None,
        description="Path to QA bug report"
    )

    # Execution tracking
    files_created: tuple[Path, ...] = Field(
        default_factory=tuple,
        description="List of files created during execution"
    )
    qa_passed: bool | None = Field(
        default=None,
        description="Whether QA tests passed (None if not yet run)"
    )
    errors: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Errors encountered during execution"
    )

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional key-value metadata"
    )
    execution_history: tuple[dict[str, Any], ...] = Field(
        default_factory=tuple,
        description="History of agent executions"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When state was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="When state was last updated"
    )

    @field_validator("current_phase")
    @classmethod
    def validate_phase(cls, v: str) -> str:
        """Validate that phase is one of the allowed values."""
        valid_phases = {"pm", "arch", "eng", "qa", "complete", "failed"}
        v_lower = v.lower()
        if v_lower not in valid_phases:
            raise ValueError(
                f"Invalid phase '{v}'. Must be one of: {', '.join(valid_phases)}"
            )
        return v_lower

    @field_validator("work_dir", mode="before")
    @classmethod
    def validate_work_dir(cls, v: Path | str) -> Path:
        """Ensure work_dir is a resolved Path."""
        if isinstance(v, str):
            v = Path(v)
        return v.resolve()

    def with_update(self, **kwargs: Any) -> AgentState:
        """Create a new state with updated values.

        This is the primary method for state updates, ensuring immutability.

        Args:
            **kwargs: Fields to update.

        Returns:
            A new AgentState instance with updated values.

        Example:
            new_state = old_state.with_update(
                current_phase="arch",
                path_prd=Path("docs/PRD.md")
            )
        """
        # Get current state as dict
        current = self.model_dump()

        # Update timestamp
        kwargs["updated_at"] = datetime.now()

        # Merge updates
        current.update(kwargs)

        return AgentState(**current)

    def add_file(self, file_path: Path) -> AgentState:
        """Add a file to the files_created list.

        Args:
            file_path: Path to the file to add.

        Returns:
            New AgentState with file added.
        """
        files = list(self.files_created)
        if file_path not in files:
            files.append(file_path)
        return self.with_update(files_created=tuple(files))

    def add_files(self, file_paths: list[Path]) -> AgentState:
        """Add multiple files to the files_created list.

        Args:
            file_paths: Paths to the files to add.

        Returns:
            New AgentState with files added.
        """
        files = list(self.files_created)
        for path in file_paths:
            if path not in files:
                files.append(path)
        return self.with_update(files_created=tuple(files))

    def add_error(self, error: str) -> AgentState:
        """Add an error to the errors list.

        Args:
            error: Error message to add.

        Returns:
            New AgentState with error added.
        """
        errors = list(self.errors)
        errors.append(error)
        return self.with_update(errors=tuple(errors))

    def add_execution(self, metrics: ExecutionMetrics, agent_name: str) -> AgentState:
        """Record execution metrics in history.

        Args:
            metrics: The execution metrics to record.
            agent_name: Name of the agent that executed.

        Returns:
            New AgentState with execution recorded.
        """
        history = list(self.execution_history)
        history.append({
            "agent": agent_name,
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics.model_dump(),
        })
        return self.with_update(execution_history=tuple(history))

    def transition_to(self, phase: str) -> AgentState:
        """Transition to the next phase.

        Args:
            phase: The phase to transition to.

        Returns:
            New AgentState with updated phase.
        """
        return self.with_update(current_phase=phase)

    def mark_failed(self, error: str) -> AgentState:
        """Mark the pipeline as failed with an error.

        Args:
            error: The error message.

        Returns:
            New AgentState marked as failed.
        """
        return self.add_error(error).with_update(current_phase="failed")

    def mark_complete(self) -> AgentState:
        """Mark the pipeline as complete.

        Returns:
            New AgentState marked as complete.
        """
        return self.with_update(current_phase="complete")

    def get_total_cost(self) -> float:
        """Calculate total estimated cost from execution history.

        Returns:
            Total estimated cost in USD.
        """
        total = 0.0
        for execution in self.execution_history:
            metrics = execution.get("metrics", {})
            total += metrics.get("estimated_cost_usd", 0.0)
        return total

    def get_total_tokens(self) -> int:
        """Calculate total tokens used from execution history.

        Returns:
            Total tokens consumed.
        """
        total = 0
        for execution in self.execution_history:
            metrics = execution.get("metrics", {})
            total += metrics.get("tokens_input", 0)
            total += metrics.get("tokens_output", 0)
        return total

    def has_artifact(self, artifact_type: str) -> bool:
        """Check if a specific artifact has been created.

        Args:
            artifact_type: One of 'prd', 'tech_spec', 'scaffold', 'bug_report'.

        Returns:
            True if the artifact exists, False otherwise.
        """
        artifact_map = {
            "prd": self.path_prd,
            "tech_spec": self.path_tech_spec,
            "scaffold": self.path_scaffold_script,
            "bug_report": self.path_bug_report,
        }
        path = artifact_map.get(artifact_type)
        return path is not None and path.exists()


def create_initial_state(
    mission: str,
    project_name: str = "project",
    work_dir: Path | None = None,
) -> AgentState:
    """Factory function to create initial pipeline state.

    Args:
        mission: The user's mission/request.
        project_name: Name of the project.
        work_dir: Working directory (defaults to current directory).

    Returns:
        A new AgentState ready for the pipeline.
    """
    return AgentState(
        mission=mission,
        project_name=project_name,
        work_dir=work_dir or Path.cwd(),
        current_phase="pm",
    )
