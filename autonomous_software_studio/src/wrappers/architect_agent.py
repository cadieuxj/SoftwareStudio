"""Software Architect Agent for generating Technical Specifications.

The Architect Agent is the second stage of the Four-Persona Waterfall pipeline.
It reads the PRD and produces a comprehensive technical specification and scaffold script.
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


class TechSpecValidationError(ArtifactValidationError):
    """Raised when technical specification validation fails."""

    pass


class ScaffoldValidationError(ArtifactValidationError):
    """Raised when scaffold script validation fails."""

    pass


class ArchitectAgent(BaseAgent):
    """Software Architect Agent for technical specification generation.

    This agent is responsible for:
    - Reading the PRD from the previous stage
    - Designing the system architecture
    - Generating a comprehensive Technical Specification
    - Creating a scaffold.sh script to set up the project structure

    The Architect sees the PRD but not the PM's conversation history.
    It translates WHAT (PRD) into HOW (Technical Specification).

    Attributes:
        OUTPUT_DIR: Directory where artifacts will be saved.
        TECH_SPEC_FILE: Filename for the technical specification.
        SCAFFOLD_FILE: Filename for the scaffold script.
        REQUIRED_SPEC_SECTIONS: Sections required in the tech spec.
    """

    OUTPUT_DIR: ClassVar[str] = "docs"
    TECH_SPEC_FILE: ClassVar[str] = "TECH_SPEC.md"
    SCAFFOLD_FILE: ClassVar[str] = "scaffold.sh"
    REQUIRED_SPEC_SECTIONS: ClassVar[list[str]] = [
        "Architecture Overview",
        "Directory Structure",
        "Data Models",
        "API Signatures",
        "Third-Party Dependencies",
        "Rules of Engagement",
    ]

    def __init__(
        self,
        env_manager: "EnvironmentManager | None" = None,
        timeout: int | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize Architect Agent with appropriate timeout."""
        super().__init__(
            env_manager=env_manager,
            timeout=timeout or 300,  # 5 minutes for architecture work
            log_dir=log_dir,
        )

    @property
    def profile_name(self) -> str:
        """Return the Architect profile name."""
        return "arch"

    @property
    def role_description(self) -> str:
        """Return the Architect role description."""
        return (
            "Pragmatic Systems Architect with expertise in scalable software design. "
            "Transforms Product Requirements into Technical Specifications."
        )

    def execute(self, state: AgentState) -> AgentState:
        """Execute the Architect agent to generate technical specification.

        Args:
            state: The current pipeline state with PRD path.

        Returns:
            Updated state with path_tech_spec and path_scaffold_script.

        Raises:
            AgentError: If specification generation fails.
            ArtifactValidationError: If PRD is missing.
            TechSpecValidationError: If generated spec is invalid.
            ScaffoldValidationError: If scaffold script is invalid.
        """
        self._logger.info("Starting Architect agent execution")

        # Validate PRD exists
        try:
            self.validate_required_artifacts(state, ["prd"])
        except ArtifactValidationError as e:
            self._logger.error(f"PRD validation failed: {e}")
            return state.add_error(str(e)).mark_failed(str(e))

        # Ensure docs directory exists
        docs_dir = state.work_dir / self.OUTPUT_DIR
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Build the prompt with PRD context
        system_prompt = self.get_system_prompt(state)
        execution_prompt = self._build_execution_prompt(state, system_prompt)

        # Execute Claude to generate artifacts
        result = self._execute_claude(
            prompt=execution_prompt,
            work_dir=state.work_dir,
        )

        if not result.success:
            error_msg = f"Technical specification generation failed: {result.stderr}"
            self._logger.error(error_msg)
            return state.add_error(error_msg).mark_failed(error_msg)

        # Determine artifact paths
        tech_spec_path = docs_dir / self.TECH_SPEC_FILE
        scaffold_path = docs_dir / self.SCAFFOLD_FILE

        # Check if artifacts were created
        if not tech_spec_path.exists():
            # Try to extract from output
            spec_content = self._extract_spec_from_output(result.stdout)
            if spec_content:
                tech_spec_path.write_text(spec_content, encoding="utf-8")
                self._logger.info(f"Extracted and saved tech spec to: {tech_spec_path}")

        if not scaffold_path.exists():
            # Try to extract from output
            scaffold_content = self._extract_scaffold_from_output(result.stdout)
            if scaffold_content:
                scaffold_path.write_text(scaffold_content, encoding="utf-8")
                scaffold_path.chmod(0o755)  # Make executable
                self._logger.info(f"Extracted and saved scaffold to: {scaffold_path}")

        # Validate tech spec
        if not tech_spec_path.exists():
            error_msg = "Technical specification file was not created"
            self._logger.error(error_msg)
            return state.add_error(error_msg).mark_failed(error_msg)

        try:
            if not self.validate_output(tech_spec_path):
                return state.add_error("Tech spec validation failed").mark_failed(
                    "Tech spec validation failed"
                )
        except TechSpecValidationError as e:
            self._logger.error(f"Tech spec validation error: {e}")
            return state.add_error(str(e)).mark_failed(str(e))

        # Validate scaffold script (if created)
        if scaffold_path.exists():
            try:
                self._validate_scaffold(scaffold_path)
            except ScaffoldValidationError as e:
                self._logger.warning(f"Scaffold validation warning: {e}")
                # Don't fail for scaffold issues, just warn

        # Calculate metrics
        metrics = self._calculate_metrics(result)

        # Build file list
        files = [tech_spec_path]
        if scaffold_path.exists():
            files.append(scaffold_path)

        # Update state
        new_state = (
            state.with_update(
                path_tech_spec=tech_spec_path,
                path_scaffold_script=scaffold_path if scaffold_path.exists() else None,
            )
            .add_files(files)
            .add_execution(metrics, self.profile_name)
            .transition_to("eng")  # Ready for Engineer
        )

        self._logger.info(
            f"Architect agent completed. Tech spec: {tech_spec_path}, "
            f"Scaffold: {scaffold_path if scaffold_path.exists() else 'N/A'}"
        )
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
        # Read PRD content
        prd_content = "[PRD not available]"
        if state.path_prd and state.path_prd.exists():
            prd_content = state.path_prd.read_text(encoding="utf-8")

        prompt = f"""
{system_prompt}

---

## Product Requirements Document

{prd_content}

---

## Instructions

Based on the PRD above, please generate:

1. **Technical Specification** (docs/TECH_SPEC.md):
   - Architecture Overview with Mermaid diagram
   - Directory Structure
   - Data Models (Pydantic/SQLAlchemy format)
   - API Signatures (OpenAPI format)
   - Third-Party Dependencies with versions
   - Rules of Engagement for Engineers

2. **Scaffold Script** (docs/scaffold.sh):
   - Create all directories from the structure
   - Create empty placeholder files with TODO comments
   - Make the script executable

Ensure the tech spec is comprehensive and provides clear guidance for
the engineering team. The scaffold script should create a working project
structure that matches the specification.
"""
        return prompt.strip()

    def _extract_spec_from_output(self, output: str) -> str | None:
        """Extract technical specification from Claude's output.

        Args:
            output: The stdout from Claude execution.

        Returns:
            Tech spec content if found, None otherwise.
        """
        patterns = [
            r"```markdown\s*(# Technical Specification.*?)```",
            r"```md\s*(# Technical Specification.*?)```",
            r"(# Technical Specification\s*\n.*?)(?=\n```|\Z)",
            r"(# TECH_SPEC\s*\n.*?)(?=\n```|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                if len(content) > 300:
                    return content

        return None

    def _extract_scaffold_from_output(self, output: str) -> str | None:
        """Extract scaffold script from Claude's output.

        Args:
            output: The stdout from Claude execution.

        Returns:
            Scaffold script content if found, None otherwise.
        """
        patterns = [
            r"```(?:bash|sh)\s*(#!/bin/bash.*?)```",
            r"```(?:bash|sh)\s*(#!/usr/bin/env bash.*?)```",
            r"(#!/bin/bash\s*\n.*?)(?=\n```|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.DOTALL)
            if match:
                content = match.group(1).strip()
                if "mkdir" in content:  # Sanity check
                    return content

        return None

    def validate_output(self, artifact_path: Path) -> bool:
        """Validate the generated technical specification.

        Validation rules:
        - Must define directory structure
        - Must define data models
        - Must define API signatures
        - Must list third-party libraries with versions
        - Must include architecture diagram (Mermaid)

        Args:
            artifact_path: Path to the tech spec file.

        Returns:
            True if tech spec is valid.

        Raises:
            TechSpecValidationError: If validation fails.
        """
        if not artifact_path.exists():
            raise TechSpecValidationError(f"Tech spec file not found: {artifact_path}")

        try:
            content = artifact_path.read_text(encoding="utf-8")
        except Exception as e:
            raise TechSpecValidationError(f"Failed to read tech spec: {e}") from e

        # Check for required sections
        missing_sections = []
        for section in self.REQUIRED_SPEC_SECTIONS:
            patterns = [
                rf"##\s*\d*\.?\s*{re.escape(section)}",
                rf"#\s*{re.escape(section)}",
                rf"\*\*{re.escape(section)}\*\*",
            ]
            found = any(
                re.search(pattern, content, re.IGNORECASE) for pattern in patterns
            )
            if not found:
                missing_sections.append(section)

        if missing_sections:
            raise TechSpecValidationError(
                f"Tech spec missing required sections: {', '.join(missing_sections)}"
            )

        # Check for Mermaid diagram
        if not re.search(r"```mermaid", content, re.IGNORECASE):
            self._logger.warning("Tech spec may be missing Mermaid architecture diagram")

        # Check for version numbers in dependencies
        if "Dependencies" in content:
            # Look for version patterns like ">=1.0.0" or "==2.0"
            deps_section = re.search(
                r"Dependencies.*?(?=##|\Z)", content, re.DOTALL | re.IGNORECASE
            )
            if deps_section:
                deps_text = deps_section.group(0)
                if not re.search(r"[>=<~^]\s*\d+\.\d+", deps_text):
                    self._logger.warning(
                        "Dependencies may not have version numbers specified"
                    )

        self._logger.info(
            f"Tech spec validation passed: {len(self.REQUIRED_SPEC_SECTIONS)} sections present"
        )
        return True

    def _validate_scaffold(self, scaffold_path: Path) -> bool:
        """Validate the scaffold script.

        Validation rules:
        - Must have shebang
        - Must contain mkdir commands
        - Must be executable or set executable

        Args:
            scaffold_path: Path to scaffold.sh.

        Returns:
            True if valid.

        Raises:
            ScaffoldValidationError: If validation fails.
        """
        if not scaffold_path.exists():
            raise ScaffoldValidationError(f"Scaffold file not found: {scaffold_path}")

        content = scaffold_path.read_text(encoding="utf-8")

        # Check shebang
        if not content.startswith("#!"):
            raise ScaffoldValidationError("Scaffold script missing shebang (#!/bin/bash)")

        # Check for directory creation
        if "mkdir" not in content:
            raise ScaffoldValidationError("Scaffold script doesn't create directories")

        # Check for file creation
        if "touch" not in content and ">" not in content and "cat" not in content:
            self._logger.warning("Scaffold script may not create placeholder files")

        # Check permissions
        import stat
        mode = scaffold_path.stat().st_mode
        if not (mode & stat.S_IXUSR):
            # Try to make executable
            scaffold_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            self._logger.info("Made scaffold.sh executable")

        return True


def main() -> None:
    """Entry point for testing Architect agent standalone."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Architect Agent - Tech Spec Generation")
    parser.add_argument(
        "--prd",
        type=str,
        required=True,
        help="Path to the PRD file",
    )
    parser.add_argument(
        "--work-dir",
        type=str,
        default=".",
        help="Working directory for execution",
    )

    args = parser.parse_args()

    # Create state with PRD
    from src.wrappers.state import create_initial_state

    prd_path = Path(args.prd)
    if not prd_path.exists():
        print(f"Error: PRD file not found: {prd_path}")
        return

    state = create_initial_state(
        mission="Generate technical specification",
        work_dir=Path(args.work_dir),
    ).with_update(path_prd=prd_path, current_phase="arch")

    # Execute Architect agent
    agent = ArchitectAgent()
    print(f"Architect Agent Info: {json.dumps(agent.get_agent_info(), indent=2)}")
    print(f"\nExecuting with PRD: {args.prd}")
    print("-" * 50)

    try:
        new_state = agent.execute(state)
        print(f"\nExecution completed:")
        print(f"  Phase: {new_state.current_phase}")
        print(f"  Tech Spec: {new_state.path_tech_spec}")
        print(f"  Scaffold: {new_state.path_scaffold_script}")
        print(f"  Errors: {new_state.errors}")
    except Exception as e:
        print(f"\nExecution failed: {e}")
        raise


if __name__ == "__main__":
    main()
