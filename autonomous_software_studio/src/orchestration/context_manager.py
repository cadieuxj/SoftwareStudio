"""Context Manager for dynamic CLAUDE.md generation.

This module handles the creation and management of CLAUDE.md context files
for each phase of the multi-agent orchestration pipeline. It provides
phase-specific context injection to guide agent behavior.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

# Maximum file size for CLAUDE.md (50KB)
MAX_CONTEXT_SIZE = 50 * 1024


class ContextSizeExceededError(Exception):
    """Raised when context exceeds maximum allowed size."""

    pass


class ContextError(Exception):
    """Raised when there is an error with context management."""

    pass


@dataclass
class PhaseContext:
    """Context data for a specific phase.

    Attributes:
        phase_name: Name of the current phase.
        mission: The project mission statement.
        guidelines: Phase-specific guidelines.
        artifacts: List of available artifacts.
        rules: Rules of engagement for the agent.
        metadata: Additional metadata for the phase.
    """

    phase_name: str
    mission: str = ""
    guidelines: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """Manages CLAUDE.md context files for multi-agent orchestration.

    This class handles:
    - Phase-specific context generation
    - Dynamic content updates
    - File size limits and validation
    - Backup management
    - Version control integration

    Example:
        >>> manager = ContextManager()
        >>> manager.update_context("pm", {"mission": "Build a task app"})
        >>> path = manager.generate_claude_md(Path("./project"))
        >>> print(path)
    """

    # Phase name mappings
    PHASES: ClassVar[dict[str, str]] = {
        "pm": "Product Manager",
        "arch": "Architect",
        "eng": "Engineer",
        "qa": "Quality Assurance",
    }

    # Default phase guidelines templates
    PHASE_TEMPLATES: ClassVar[dict[str, dict[str, Any]]] = {
        "pm": {
            "role": "Product Manager",
            "focus": "Requirements and user stories",
            "default_guidelines": [
                "Focus on user needs and business value",
                "Create clear, measurable acceptance criteria",
                "Prioritize features based on impact and effort",
                "Document assumptions and constraints",
                "Consider edge cases and error scenarios",
            ],
            "default_rules": [
                "Generate PRD document in docs/prd.md",
                "Use clear, non-technical language where possible",
                "Include success metrics for each feature",
                "Mark required vs optional features",
            ],
        },
        "arch": {
            "role": "Software Architect",
            "focus": "Technical design and system structure",
            "default_guidelines": [
                "Design for scalability and maintainability",
                "Choose appropriate design patterns",
                "Consider security implications",
                "Document trade-offs and decisions",
                "Create clear component boundaries",
            ],
            "default_rules": [
                "Generate technical spec in docs/architecture.md",
                "Include system diagrams where helpful",
                "Reference the PRD requirements",
                "Define API contracts and interfaces",
            ],
        },
        "eng": {
            "role": "Software Engineer",
            "focus": "Implementation and code quality",
            "default_guidelines": [
                "Follow established coding standards",
                "Write clean, readable code",
                "Include appropriate error handling",
                "Add tests for critical functionality",
                "Document complex logic with comments",
            ],
            "default_rules": [
                "Implement according to the technical spec",
                "Create modular, reusable components",
                "Follow the project's file structure",
                "Commit changes with clear messages",
            ],
        },
        "qa": {
            "role": "Quality Assurance Engineer",
            "focus": "Testing and validation",
            "default_guidelines": [
                "Test against acceptance criteria",
                "Cover edge cases and error scenarios",
                "Verify security requirements",
                "Check performance benchmarks",
                "Document test results clearly",
            ],
            "default_rules": [
                "Generate test report in reports/qa_report.md",
                "Include pass/fail status for each criterion",
                "List any bugs or issues found",
                "Provide recommendations for fixes",
            ],
        },
    }

    def __init__(
        self,
        backup_dir: Path | None = None,
        max_size: int = MAX_CONTEXT_SIZE,
    ) -> None:
        """Initialize the ContextManager.

        Args:
            backup_dir: Directory for context backups. Defaults to ./backups.
            max_size: Maximum size for CLAUDE.md in bytes. Defaults to 50KB.
        """
        self._backup_dir = backup_dir or Path("backups")
        self._max_size = max_size
        self._current_context: PhaseContext | None = None
        self._custom_rules: list[str] = []
        self._version = 0

    def update_context(self, phase: str, content: dict[str, Any]) -> None:
        """Update the context for a specific phase.

        Args:
            phase: The phase name (pm, arch, eng, qa).
            content: Dictionary with context content including:
                - mission: Project mission statement
                - guidelines: List of phase-specific guidelines
                - artifacts: List of available artifacts
                - rules: Additional rules of engagement
                - metadata: Additional key-value metadata

        Raises:
            ContextError: If phase is invalid.
        """
        phase = phase.lower()

        if phase not in self.PHASES:
            valid_phases = ", ".join(self.PHASES.keys())
            raise ContextError(
                f"Invalid phase '{phase}'. Valid phases are: {valid_phases}"
            )

        # Get default template for the phase
        template = self.PHASE_TEMPLATES.get(phase, {})

        # Merge content with defaults
        guidelines = content.get("guidelines", template.get("default_guidelines", []))
        rules = content.get("rules", template.get("default_rules", []))

        self._current_context = PhaseContext(
            phase_name=phase,
            mission=content.get("mission", ""),
            guidelines=guidelines,
            artifacts=content.get("artifacts", []),
            rules=rules + self._custom_rules,
            metadata=content.get("metadata", {}),
        )

        self._version += 1

    def generate_claude_md(self, work_dir: Path) -> Path:
        """Generate CLAUDE.md file in the working directory.

        Args:
            work_dir: The directory where CLAUDE.md will be created.

        Returns:
            Path to the generated CLAUDE.md file.

        Raises:
            ContextError: If no context has been set.
            ContextSizeExceededError: If generated content exceeds size limit.
        """
        if self._current_context is None:
            raise ContextError(
                "No context set. Call update_context() before generating."
            )

        work_dir = Path(work_dir).resolve()
        work_dir.mkdir(parents=True, exist_ok=True)

        claude_md_path = work_dir / "CLAUDE.md"

        # Backup existing file if present
        if claude_md_path.exists():
            self._backup_file(claude_md_path)

        # Generate content
        content = self._generate_content()

        # Check size limit
        content_size = len(content.encode("utf-8"))
        if content_size > self._max_size:
            raise ContextSizeExceededError(
                f"Generated context ({content_size} bytes) exceeds limit "
                f"({self._max_size} bytes). Consider reducing content."
            )

        # Write atomically (write to temp, then rename)
        temp_path = work_dir / ".CLAUDE.md.tmp"
        try:
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(claude_md_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise ContextError(f"Failed to write CLAUDE.md: {e}") from e

        return claude_md_path

    def _generate_content(self) -> str:
        """Generate the CLAUDE.md content from current context.

        Returns:
            The formatted markdown content.
        """
        ctx = self._current_context
        if ctx is None:
            return ""

        phase_display = self.PHASES.get(ctx.phase_name, ctx.phase_name)
        template = self.PHASE_TEMPLATES.get(ctx.phase_name, {})
        role = template.get("role", phase_display)
        focus = template.get("focus", "")

        lines = [
            "# Project Context",
            "",
            f"## Current Phase: {phase_display}",
            "",
            f"**Role**: {role}",
            f"**Focus**: {focus}",
            "",
        ]

        # Project Mission
        if ctx.mission:
            lines.extend([
                "## Project Mission",
                "",
                ctx.mission,
                "",
            ])

        # Phase-Specific Guidelines
        if ctx.guidelines:
            lines.extend([
                "## Phase-Specific Guidelines",
                "",
            ])
            for guideline in ctx.guidelines:
                lines.append(f"- {guideline}")
            lines.append("")

        # Artifacts Available
        if ctx.artifacts:
            lines.extend([
                "## Artifacts Available",
                "",
            ])
            for artifact in ctx.artifacts:
                lines.append(f"- {artifact}")
            lines.append("")

        # Rules of Engagement
        if ctx.rules:
            lines.extend([
                "## Rules of Engagement",
                "",
            ])
            for rule in ctx.rules:
                lines.append(f"- {rule}")
            lines.append("")

        # Metadata
        if ctx.metadata:
            lines.extend([
                "## Additional Context",
                "",
            ])
            for key, value in ctx.metadata.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        # Footer with version info
        lines.extend([
            "---",
            "",
            f"*Generated by Autonomous Software Studio - Version {self._version}*",
            f"*Phase: {ctx.phase_name} | Generated: {datetime.now().isoformat()}*",
        ])

        return "\n".join(lines)

    def clear_context(self) -> None:
        """Clear the current context."""
        self._current_context = None
        self._custom_rules.clear()
        self._version = 0

    def append_rules(self, rules: list[str]) -> None:
        """Append additional rules to be included in all contexts.

        Args:
            rules: List of rules to append.
        """
        self._custom_rules.extend(rules)

        # Update current context if present
        if self._current_context is not None:
            self._current_context.rules.extend(rules)

    def _backup_file(self, file_path: Path) -> Path:
        """Create a backup of the specified file.

        Args:
            file_path: Path to the file to backup.

        Returns:
            Path to the backup file.
        """
        self._backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self._backup_dir / backup_name

        shutil.copy2(file_path, backup_path)

        return backup_path

    def get_context_info(self) -> dict[str, Any]:
        """Get information about the current context.

        Returns:
            Dictionary containing context information.
        """
        if self._current_context is None:
            return {
                "has_context": False,
                "version": self._version,
                "custom_rules_count": len(self._custom_rules),
            }

        return {
            "has_context": True,
            "phase": self._current_context.phase_name,
            "mission_set": bool(self._current_context.mission),
            "guideline_count": len(self._current_context.guidelines),
            "artifact_count": len(self._current_context.artifacts),
            "rule_count": len(self._current_context.rules),
            "version": self._version,
            "custom_rules_count": len(self._custom_rules),
        }

    def get_phase_template(self, phase: str) -> dict[str, Any]:
        """Get the default template for a phase.

        Args:
            phase: The phase name.

        Returns:
            Dictionary containing the phase template.
        """
        return self.PHASE_TEMPLATES.get(phase.lower(), {})


def generate_sample_contexts(output_dir: Path) -> list[Path]:
    """Generate sample CLAUDE.md files for each phase.

    Args:
        output_dir: Directory to write sample files.

    Returns:
        List of paths to generated files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manager = ContextManager()
    generated_files: list[Path] = []

    sample_mission = """Build a modern task management application that helps teams
collaborate effectively. The application should support task creation,
assignment, due dates, and status tracking with a clean, intuitive interface."""

    for phase in ["pm", "arch", "eng", "qa"]:
        # Create phase-specific work directory
        phase_dir = output_dir / f"sample_{phase}"
        phase_dir.mkdir(parents=True, exist_ok=True)

        # Set up context for this phase
        artifacts = []
        if phase == "arch":
            artifacts = ["docs/prd.md - Product Requirements Document"]
        elif phase == "eng":
            artifacts = [
                "docs/prd.md - Product Requirements Document",
                "docs/architecture.md - Technical Architecture",
            ]
        elif phase == "qa":
            artifacts = [
                "docs/prd.md - Product Requirements Document",
                "docs/architecture.md - Technical Architecture",
                "src/ - Implementation code",
            ]

        manager.update_context(
            phase,
            {
                "mission": sample_mission,
                "artifacts": artifacts,
                "metadata": {
                    "project_name": "TaskFlow",
                    "target_platform": "Web",
                    "priority": "High",
                },
            },
        )

        # Generate CLAUDE.md
        path = manager.generate_claude_md(phase_dir)
        generated_files.append(path)

        # Reset for next phase
        manager.clear_context()

    return generated_files


def main() -> None:
    """Entry point for testing the context manager."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--generate-samples":
        output_dir = Path("docs/samples")
        paths = generate_sample_contexts(output_dir)
        print("Generated sample CLAUDE.md files:")
        for path in paths:
            print(f"  - {path}")
    else:
        # Show context info
        manager = ContextManager()
        print("Context Manager - Test Mode")
        print("-" * 40)
        print(f"Available phases: {list(manager.PHASES.keys())}")
        print(f"Max context size: {MAX_CONTEXT_SIZE} bytes")
        print("\nRun with --generate-samples to create sample contexts")


if __name__ == "__main__":
    main()
