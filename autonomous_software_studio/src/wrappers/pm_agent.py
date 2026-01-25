"""Product Manager Agent for generating Product Requirements Documents.

The PM Agent is the first stage of the Four-Persona Waterfall pipeline.
It analyzes the user's mission and generates a comprehensive PRD.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from src.wrappers.base_agent import (
    AgentError,
    ArtifactValidationError,
    BaseAgent,
)
from src.wrappers.state import AgentState

if TYPE_CHECKING:
    from src.wrappers.env_manager import EnvironmentManager


class PRDValidationError(ArtifactValidationError):
    """Raised when PRD validation fails."""

    pass


class PMAgent(BaseAgent):
    """Product Manager Agent for PRD generation.

    This agent is responsible for:
    - Understanding the user's mission/requirements
    - Generating a comprehensive Product Requirements Document
    - Ensuring all required sections are present
    - Using mcp-browser for research if configured

    The PM agent is forbidden from discussing code implementation -
    it focuses solely on WHAT the system should do, not HOW.

    Attributes:
        OUTPUT_DIR: Directory where PRD will be saved.
        OUTPUT_FILE: Filename for the PRD.
        REQUIRED_SECTIONS: Sections that must be present in the PRD.
        MIN_WORD_COUNT: Minimum word count for a valid PRD.
    """

    OUTPUT_DIR: ClassVar[str] = "docs"
    OUTPUT_FILE: ClassVar[str] = "PRD.md"
    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "User Stories",
        "Functional Requirements",
        "Non-Functional Requirements",
        "Acceptance Criteria",
    ]
    MIN_WORD_COUNT: ClassVar[int] = 500

    def __init__(
        self,
        env_manager: "EnvironmentManager | None" = None,
        timeout: int | None = None,
        log_dir: "Path | None" = None,
    ) -> None:
        """Initialize PM Agent with 180 second timeout."""
        # PM agent has a specific timeout of 180 seconds
        super().__init__(
            env_manager=env_manager,
            timeout=timeout or 180,
            log_dir=log_dir,
        )

    @property
    def profile_name(self) -> str:
        """Return the PM profile name."""
        return "pm"

    @property
    def role_description(self) -> str:
        """Return the PM role description."""
        return (
            "Senior Product Manager specializing in software requirements. "
            "Transforms user missions into comprehensive Product Requirements Documents."
        )

    def execute(self, state: AgentState) -> AgentState:
        """Execute the PM agent to generate a PRD.

        Args:
            state: The current pipeline state with user mission.

        Returns:
            Updated state with path_prd set to the generated PRD.

        Raises:
            AgentError: If PRD generation fails.
            PRDValidationError: If generated PRD is invalid.
        """
        self._logger.info(f"Starting PM agent execution for mission: {state.mission}")

        # Ensure docs directory exists
        docs_dir = state.work_dir / self.OUTPUT_DIR
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Build the prompt with mission context
        system_prompt = self.get_system_prompt(state)

        # Construct the execution prompt
        execution_prompt = self._build_execution_prompt(state, system_prompt)

        # Execute Claude to generate PRD
        result = self._execute_claude(
            prompt=execution_prompt,
            work_dir=state.work_dir,
        )

        if not result.success:
            error_msg = f"PRD generation failed: {result.stderr}"
            self._logger.error(error_msg)
            return state.add_error(error_msg).mark_failed(error_msg)

        # Determine PRD path
        prd_path = docs_dir / self.OUTPUT_FILE

        # Check if PRD was created
        if not prd_path.exists():
            # Try to find PRD in artifacts
            for artifact in result.artifacts_created:
                if artifact.name.upper() == "PRD.MD":
                    prd_path = artifact
                    break

        # If PRD still doesn't exist, check if Claude output contains it
        if not prd_path.exists():
            # Try to extract PRD from output and save it
            prd_content = self._extract_prd_from_output(result.stdout)
            if prd_content:
                prd_path.write_text(prd_content, encoding="utf-8")
                self._logger.info(f"Extracted and saved PRD to: {prd_path}")

        # Final check
        if not prd_path.exists():
            error_msg = "PRD file was not created by the agent"
            self._logger.error(error_msg)
            return state.add_error(error_msg).mark_failed(error_msg)

        # Validate the PRD
        try:
            if not self.validate_output(prd_path):
                return state.add_error("PRD validation failed").mark_failed(
                    "PRD validation failed"
                )
        except PRDValidationError as e:
            self._logger.error(f"PRD validation error: {e}")
            return state.add_error(str(e)).mark_failed(str(e))

        # Calculate and record metrics
        metrics = self._calculate_metrics(result)

        # Update state with PRD path and metrics
        new_state = (
            state.with_update(path_prd=prd_path)
            .add_file(prd_path)
            .add_execution(metrics, self.profile_name)
            .transition_to("arch")  # Ready for Architect
        )

        self._logger.info(f"PM agent completed successfully. PRD at: {prd_path}")
        return new_state

    def _build_execution_prompt(
        self,
        state: AgentState,
        system_prompt: str,
    ) -> str:
        """Build the full execution prompt for Claude.

        Args:
            state: Current pipeline state.
            system_prompt: The loaded system prompt template.

        Returns:
            Complete prompt for Claude execution.
        """
        prompt = f"""
{system_prompt}

---

## Current Mission

{state.mission}

---

## Instructions

Please generate a comprehensive Product Requirements Document (PRD) based on the
mission above. Save the document to docs/PRD.md.

Ensure the PRD includes all required sections:
1. User Stories (minimum 5)
2. Functional Requirements (numbered, testable)
3. Non-Functional Requirements (performance, security, scalability)
4. Acceptance Criteria (Given/When/Then format)

The document should be at least 500 words to ensure adequate detail.
"""
        return prompt.strip()

    def _extract_prd_from_output(self, output: str) -> str | None:
        """Extract PRD content from Claude's output if inline.

        Sometimes Claude may output the PRD content directly instead of
        creating a file. This method extracts it for saving.

        Args:
            output: The stdout from Claude execution.

        Returns:
            PRD content if found, None otherwise.
        """
        # Look for markdown PRD structure
        patterns = [
            r"```markdown\s*(# Product Requirements Document.*?)```",
            r"```md\s*(# Product Requirements Document.*?)```",
            r"(# Product Requirements Document\s*\n.*?)(?=\n```|\Z)",
            r"(# PRD\s*\n.*?)(?=\n```|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                if len(content) > 200:  # Sanity check
                    return content

        return None

    def validate_output(self, artifact_path: Path) -> bool:
        """Validate the generated PRD meets requirements.

        Validation rules:
        - Must contain "User Stories" section
        - Must contain "Functional Requirements" section
        - Must contain "Non-Functional Requirements" section
        - Must contain "Acceptance Criteria" section
        - Must have minimum 500 words total

        Args:
            artifact_path: Path to the PRD file.

        Returns:
            True if PRD is valid.

        Raises:
            PRDValidationError: If validation fails.
        """
        if not artifact_path.exists():
            raise PRDValidationError(f"PRD file not found: {artifact_path}")

        try:
            content = artifact_path.read_text(encoding="utf-8")
        except Exception as e:
            raise PRDValidationError(f"Failed to read PRD: {e}") from e

        # Check for required sections
        missing_sections = []
        for section in self.REQUIRED_SECTIONS:
            # Check for various header formats
            patterns = [
                rf"##\s*\d*\.?\s*{re.escape(section)}",  # ## User Stories or ## 1. User Stories
                rf"#\s*{re.escape(section)}",  # # User Stories
                rf"\*\*{re.escape(section)}\*\*",  # **User Stories**
            ]
            found = any(
                re.search(pattern, content, re.IGNORECASE) for pattern in patterns
            )
            if not found:
                missing_sections.append(section)

        if missing_sections:
            raise PRDValidationError(
                f"PRD missing required sections: {', '.join(missing_sections)}"
            )

        # Check word count
        words = len(content.split())
        if words < self.MIN_WORD_COUNT:
            raise PRDValidationError(
                f"PRD has only {words} words. Minimum required: {self.MIN_WORD_COUNT}"
            )

        # Check for user stories format (As a... I want... so that...)
        if not re.search(
            r"[Aa]s an?\s+\w+.*[Ii]\s+want.*so\s+that", content, re.IGNORECASE
        ):
            self._logger.warning(
                "PRD may not have properly formatted user stories "
                "(As a... I want... so that...)"
            )

        # Check for acceptance criteria format (Given/When/Then)
        if not re.search(r"[Gg]iven.*[Ww]hen.*[Tt]hen", content, re.IGNORECASE):
            self._logger.warning(
                "PRD may not have properly formatted acceptance criteria "
                "(Given/When/Then)"
            )

        self._logger.info(
            f"PRD validation passed: {len(self.REQUIRED_SECTIONS)} sections, {words} words"
        )
        return True


def main() -> None:
    """Entry point for testing PM agent standalone."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="PM Agent - PRD Generation")
    parser.add_argument(
        "--mission",
        type=str,
        required=True,
        help="The project mission/requirements",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="docs/PRD.md",
        help="Output path for PRD",
    )
    parser.add_argument(
        "--work-dir",
        type=str,
        default=".",
        help="Working directory for execution",
    )

    args = parser.parse_args()

    # Create initial state
    from src.wrappers.state import create_initial_state

    state = create_initial_state(
        mission=args.mission,
        work_dir=Path(args.work_dir),
    )

    # Execute PM agent
    agent = PMAgent()
    print(f"PM Agent Info: {json.dumps(agent.get_agent_info(), indent=2)}")
    print(f"\nExecuting with mission: {args.mission}")
    print("-" * 50)

    try:
        new_state = agent.execute(state)
        print(f"\nExecution completed:")
        print(f"  Phase: {new_state.current_phase}")
        print(f"  PRD Path: {new_state.path_prd}")
        print(f"  Errors: {new_state.errors}")
    except Exception as e:
        print(f"\nExecution failed: {e}")
        raise


if __name__ == "__main__":
    main()
