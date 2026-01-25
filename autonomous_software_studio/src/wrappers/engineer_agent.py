"""Senior Engineer Agent for implementing code based on Technical Specifications.

The Engineer Agent is the third stage of the Four-Persona Waterfall pipeline.
It reads the TECH_SPEC and implements the code in batches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from src.wrappers.base_agent import (
    AgentError,
    ArtifactValidationError,
    BaseAgent,
)
from src.wrappers.state import AgentState, ExecutionMetrics

if TYPE_CHECKING:
    from src.wrappers.env_manager import EnvironmentManager


class CodeValidationError(ArtifactValidationError):
    """Raised when code validation fails."""

    pass


class BatchExecutionError(AgentError):
    """Raised when a batch execution fails."""

    pass


@dataclass
class ImplementationBatch:
    """Represents a batch of implementation work.

    Attributes:
        name: Name of the batch (e.g., 'models', 'api').
        scope: Description of what this batch covers.
        directories: Directories to focus on for this batch.
        order: Execution order (lower runs first).
    """

    name: str
    scope: str
    directories: list[str]
    order: int


class EngineerAgent(BaseAgent):
    """Senior Engineer Agent for code implementation.

    This agent is responsible for:
    - Reading the Technical Specification
    - Extracting Rules of Engagement
    - Implementing code in organized batches
    - Ensuring code quality (no TODOs, valid imports)
    - Writing corresponding unit tests

    The Engineer never sees the PRD directly - only the TECH_SPEC.
    This ensures context isolation and focused implementation.

    Attributes:
        IMPLEMENTATION_BATCHES: Ordered batches for implementation.
        FORBIDDEN_PATTERNS: Patterns that should not appear in final code.
        MIN_BATCH_LINES: Minimum lines expected per batch.
    """

    IMPLEMENTATION_BATCHES: ClassVar[list[ImplementationBatch]] = [
        ImplementationBatch(
            name="models",
            scope="Database models, Pydantic schemas, entity definitions",
            directories=["src/models", "src/schemas"],
            order=1,
        ),
        ImplementationBatch(
            name="api",
            scope="API routes, endpoints, request/response handling",
            directories=["src/api", "src/routes"],
            order=2,
        ),
        ImplementationBatch(
            name="services",
            scope="Business logic, service layer, core functionality",
            directories=["src/services", "src/core"],
            order=3,
        ),
        ImplementationBatch(
            name="frontend",
            scope="Frontend components, UI logic (if applicable)",
            directories=["src/frontend", "src/ui", "src/components"],
            order=4,
        ),
    ]

    FORBIDDEN_PATTERNS: ClassVar[list[str]] = [
        r"#\s*TODO",
        r"#\s*FIXME",
        r"#\s*XXX",
        r"pass\s*#\s*implement",
        r"\.\.\.\s*#\s*implement",
        r"raise\s+NotImplementedError",
    ]

    MIN_BATCH_LINES: ClassVar[int] = 10

    def __init__(
        self,
        env_manager: "EnvironmentManager | None" = None,
        timeout: int | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize Engineer Agent with appropriate timeout."""
        super().__init__(
            env_manager=env_manager,
            timeout=timeout or 600,  # 10 minutes for implementation
            log_dir=log_dir,
        )

    @property
    def profile_name(self) -> str:
        """Return the Engineer profile name."""
        return "eng"

    @property
    def role_description(self) -> str:
        """Return the Engineer role description."""
        return (
            "Detail-oriented Senior Developer specializing in production-quality "
            "code implementation. Transforms Technical Specifications into working software."
        )

    def execute(self, state: AgentState) -> AgentState:
        """Execute the Engineer agent to implement code.

        The implementation proceeds in batches:
        1. Database models
        2. API routes
        3. Business logic/services
        4. Frontend (if applicable)

        Args:
            state: The current pipeline state with tech spec path.

        Returns:
            Updated state with list of files created.

        Raises:
            AgentError: If implementation fails.
            ArtifactValidationError: If tech spec is missing.
            CodeValidationError: If generated code is invalid.
        """
        self._logger.info("Starting Engineer agent execution")

        # Validate tech spec exists
        try:
            self.validate_required_artifacts(state, ["tech_spec"])
        except ArtifactValidationError as e:
            self._logger.error(f"Tech spec validation failed: {e}")
            return state.add_error(str(e)).mark_failed(str(e))

        # Extract Rules of Engagement from tech spec
        rules = self._extract_rules(state)
        self._logger.info(f"Extracted {len(rules)} rules of engagement")

        # Update CLAUDE.md with spec and rules
        self._update_claude_md(state, rules)

        # Execute implementation in batches
        current_state = state
        total_files_created: list[Path] = []
        total_metrics = ExecutionMetrics()

        for batch in sorted(self.IMPLEMENTATION_BATCHES, key=lambda b: b.order):
            self._logger.info(f"Starting batch: {batch.name}")

            try:
                batch_state, batch_files, batch_metrics = self._execute_batch(
                    current_state, batch, rules
                )
                current_state = batch_state
                total_files_created.extend(batch_files)

                # Aggregate metrics
                total_metrics = ExecutionMetrics(
                    tokens_input=total_metrics.tokens_input + batch_metrics.tokens_input,
                    tokens_output=total_metrics.tokens_output + batch_metrics.tokens_output,
                    execution_time_seconds=(
                        total_metrics.execution_time_seconds
                        + batch_metrics.execution_time_seconds
                    ),
                    estimated_cost_usd=(
                        total_metrics.estimated_cost_usd + batch_metrics.estimated_cost_usd
                    ),
                )

                self._logger.info(
                    f"Batch {batch.name} completed: {len(batch_files)} files created"
                )

            except BatchExecutionError as e:
                self._logger.error(f"Batch {batch.name} failed: {e}")
                return current_state.add_error(str(e)).mark_failed(str(e))

        # Validate all generated code
        try:
            self._validate_implementation(state.work_dir, total_files_created)
        except CodeValidationError as e:
            self._logger.warning(f"Code validation warning: {e}")
            # Don't fail for warnings, but log them

        # Update state
        new_state = (
            current_state.add_files(total_files_created)
            .add_execution(total_metrics, self.profile_name)
            .transition_to("qa")  # Ready for QA
        )

        self._logger.info(
            f"Engineer agent completed. Total files: {len(total_files_created)}"
        )
        return new_state

    def _extract_rules(self, state: AgentState) -> list[str]:
        """Extract Rules of Engagement from technical specification.

        Args:
            state: Current state with tech spec path.

        Returns:
            List of rules extracted from the spec.
        """
        if not state.path_tech_spec or not state.path_tech_spec.exists():
            return []

        content = state.path_tech_spec.read_text(encoding="utf-8")

        # Find Rules of Engagement section
        patterns = [
            r"##\s*(?:\d+\.\s*)?Rules of Engagement.*?\n(.*?)(?=\n##|\Z)",
            r"###\s*Coding Standards\s*\n(.*?)(?=\n###|\n##|\Z)",
        ]

        rules: list[str] = []
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                section = match.group(1)
                # Extract bullet points
                for line in section.split("\n"):
                    line = line.strip()
                    if line.startswith("-") or line.startswith("*"):
                        rules.append(line.lstrip("-* ").strip())

        return rules

    def _update_claude_md(self, state: AgentState, rules: list[str]) -> None:
        """Update CLAUDE.md with tech spec context and rules.

        Args:
            state: Current state.
            rules: Rules of engagement to include.
        """
        claude_md_path = state.work_dir / "CLAUDE.md"

        # Read tech spec
        tech_spec = ""
        if state.path_tech_spec and state.path_tech_spec.exists():
            tech_spec = state.path_tech_spec.read_text(encoding="utf-8")

        content = f"""# Engineer Context

## Technical Specification Summary
{tech_spec[:5000] if len(tech_spec) > 5000 else tech_spec}

## Rules of Engagement
{chr(10).join(f'- {rule}' for rule in rules)}

## Implementation Guidelines
- Follow the technical specification exactly
- Do NOT add features not in the spec
- Write production-quality code
- Include comprehensive error handling
- Add type hints to all functions
- Write docstrings for all public functions
- Create unit tests for all implemented code
"""

        claude_md_path.write_text(content, encoding="utf-8")
        self._logger.info(f"Updated CLAUDE.md at {claude_md_path}")

    def _execute_batch(
        self,
        state: AgentState,
        batch: ImplementationBatch,
        rules: list[str],
    ) -> tuple[AgentState, list[Path], ExecutionMetrics]:
        """Execute a single implementation batch.

        Args:
            state: Current state.
            batch: The batch to execute.
            rules: Rules of engagement.

        Returns:
            Tuple of (updated state, files created, metrics).

        Raises:
            BatchExecutionError: If batch execution fails.
        """
        # Build batch prompt
        system_prompt = self.get_system_prompt(state)
        batch_prompt = self._build_batch_prompt(state, batch, rules, system_prompt)

        # Execute
        result = self._execute_claude(
            prompt=batch_prompt,
            work_dir=state.work_dir,
        )

        if not result.success:
            raise BatchExecutionError(
                f"Batch '{batch.name}' failed: {result.stderr}"
            )

        # Find created files
        files_created: list[Path] = []
        for directory in batch.directories:
            dir_path = state.work_dir / directory
            if dir_path.exists():
                for py_file in dir_path.rglob("*.py"):
                    if py_file not in files_created:
                        files_created.append(py_file)

        # Also check artifacts detected by wrapper
        for artifact in result.artifacts_created:
            if artifact.suffix == ".py" and artifact not in files_created:
                files_created.append(artifact)

        metrics = self._calculate_metrics(result)

        return state, files_created, metrics

    def _build_batch_prompt(
        self,
        state: AgentState,
        batch: ImplementationBatch,
        rules: list[str],
        system_prompt: str,
    ) -> str:
        """Build prompt for a specific batch.

        Args:
            state: Current state.
            batch: The batch to build prompt for.
            rules: Rules of engagement.
            system_prompt: Base system prompt.

        Returns:
            Complete batch execution prompt.
        """
        # Read tech spec for reference
        tech_spec = "[Tech spec not available]"
        if state.path_tech_spec and state.path_tech_spec.exists():
            tech_spec = state.path_tech_spec.read_text(encoding="utf-8")

        prompt = f"""
{system_prompt}

---

## Current Batch: {batch.name}

### Batch Scope
{batch.scope}

### Target Directories
{', '.join(batch.directories)}

### Technical Specification
{tech_spec}

### Rules of Engagement
{chr(10).join(f'- {rule}' for rule in rules)}

---

## Instructions

Implement the components defined in the technical specification for this batch.

Focus areas for the {batch.name} batch:
- {batch.scope}

Requirements:
1. Implement EXACTLY what the TECH_SPEC defines
2. Do NOT add features not in the spec
3. Write production-quality code (no placeholders)
4. Include comprehensive error handling
5. Add type hints to ALL functions
6. Add docstrings in Google format
7. Create unit tests in tests/ directory
8. No TODO, FIXME, or XXX comments
9. No raise NotImplementedError

After implementation, verify:
- All imports are valid
- Code passes basic syntax checks
- Tests are included for critical functions
"""
        return prompt.strip()

    def _validate_implementation(
        self,
        work_dir: Path,
        files: list[Path],
    ) -> None:
        """Validate the implemented code.

        Checks for:
        - No TODO/FIXME/XXX comments
        - No NotImplementedError
        - Valid Python syntax
        - Valid imports

        Args:
            work_dir: Working directory.
            files: List of files to validate.

        Raises:
            CodeValidationError: If validation fails.
        """
        issues: list[str] = []

        for file_path in files:
            if not file_path.exists():
                continue

            if file_path.suffix != ".py":
                continue

            content = file_path.read_text(encoding="utf-8")

            # Check for forbidden patterns
            for pattern in self.FORBIDDEN_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    issues.append(
                        f"{file_path.name}: Found forbidden pattern '{pattern}'"
                    )

            # Check Python syntax
            try:
                compile(content, str(file_path), "exec")
            except SyntaxError as e:
                issues.append(f"{file_path.name}: Syntax error at line {e.lineno}")

        if issues:
            self._logger.warning(f"Code validation found {len(issues)} issues:")
            for issue in issues[:10]:  # Log first 10
                self._logger.warning(f"  - {issue}")

            if len(issues) > 5:
                raise CodeValidationError(
                    f"Found {len(issues)} code quality issues. "
                    f"First issue: {issues[0]}"
                )

    def validate_output(self, artifact_path: Path) -> bool:
        """Validate a generated code file.

        Args:
            artifact_path: Path to the code file.

        Returns:
            True if code is valid.
        """
        if not artifact_path.exists():
            return False

        if artifact_path.suffix != ".py":
            return True  # Non-Python files pass

        content = artifact_path.read_text(encoding="utf-8")

        # Check for forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                self._logger.warning(
                    f"File {artifact_path.name} contains forbidden pattern"
                )
                return False

        # Check syntax
        try:
            compile(content, str(artifact_path), "exec")
        except SyntaxError:
            return False

        return True


def main() -> None:
    """Entry point for testing Engineer agent standalone."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Engineer Agent - Code Implementation")
    parser.add_argument(
        "--tech-spec",
        type=str,
        required=True,
        help="Path to the technical specification",
    )
    parser.add_argument(
        "--work-dir",
        type=str,
        default=".",
        help="Working directory for execution",
    )
    parser.add_argument(
        "--batch",
        type=str,
        choices=["models", "api", "services", "frontend", "all"],
        default="all",
        help="Batch to execute (default: all)",
    )

    args = parser.parse_args()

    # Create state
    from src.wrappers.state import create_initial_state

    spec_path = Path(args.tech_spec)
    if not spec_path.exists():
        print(f"Error: Tech spec not found: {spec_path}")
        return

    state = create_initial_state(
        mission="Implement from technical specification",
        work_dir=Path(args.work_dir),
    ).with_update(path_tech_spec=spec_path, current_phase="eng")

    # Execute
    agent = EngineerAgent()
    print(f"Engineer Agent Info: {json.dumps(agent.get_agent_info(), indent=2)}")
    print(f"\nExecuting with tech spec: {args.tech_spec}")
    print("-" * 50)

    try:
        new_state = agent.execute(state)
        print(f"\nExecution completed:")
        print(f"  Phase: {new_state.current_phase}")
        print(f"  Files created: {len(new_state.files_created)}")
        for f in new_state.files_created[:10]:
            print(f"    - {f}")
        print(f"  Errors: {new_state.errors}")
    except Exception as e:
        print(f"\nExecution failed: {e}")
        raise


if __name__ == "__main__":
    main()
