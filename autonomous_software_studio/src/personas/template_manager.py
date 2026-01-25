"""Prompt Template Management System.

This module provides template loading, rendering, and validation
for persona system prompts using Jinja2 templating.
"""

from __future__ import annotations

import hashlib
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    Template,
    TemplateSyntaxError,
    Undefined,
    UndefinedError,
    meta,
)

logger = logging.getLogger(__name__)


class TemplateError(Exception):
    """Base exception for template errors."""

    pass


class TemplateNotFoundError(TemplateError):
    """Raised when a template file is not found."""

    pass


class TemplateRenderError(TemplateError):
    """Raised when template rendering fails."""

    pass


class TemplateValidationError(TemplateError):
    """Raised when template validation fails."""

    pass


@dataclass
class TemplateVariable:
    """Metadata about a template variable.

    Attributes:
        name: Variable name.
        description: Description of the variable's purpose.
        required: Whether the variable is required.
        default: Default value if not required.
        example: Example value for documentation.
    """

    name: str
    description: str = ""
    required: bool = True
    default: str | None = None
    example: str | None = None


@dataclass
class TemplateMetadata:
    """Metadata about a prompt template.

    Attributes:
        persona: The persona name (pm, arch, eng, qa).
        version: Template version (from git or hash).
        variables: List of template variables.
        last_modified: Last modification timestamp.
        file_path: Path to the template file.
        content_hash: SHA256 hash of the content.
    """

    persona: str
    version: str
    variables: list[TemplateVariable]
    last_modified: datetime | None
    file_path: Path
    content_hash: str


@dataclass
class ValidationResult:
    """Result of template validation.

    Attributes:
        is_valid: Whether the template is valid.
        errors: List of error messages.
        warnings: List of warning messages.
        missing_variables: Variables referenced but not defined.
        unused_variables: Variables in context but not used.
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_variables: list[str] = field(default_factory=list)
    unused_variables: list[str] = field(default_factory=list)


# Expected variables for each persona template
PERSONA_VARIABLES: dict[str, list[TemplateVariable]] = {
    "pm": [
        TemplateVariable(
            name="user_mission",
            description="The user's mission or project request",
            required=True,
            example="Build a task management application with real-time collaboration",
        ),
    ],
    "arch": [
        TemplateVariable(
            name="prd_content",
            description="The Product Requirements Document content",
            required=True,
            example="# PRD\n## User Stories\n...",
        ),
    ],
    "eng": [
        TemplateVariable(
            name="tech_spec_content",
            description="The Technical Specification content",
            required=True,
            example="# Technical Specification\n## Architecture\n...",
        ),
        TemplateVariable(
            name="rules_of_engagement",
            description="Coding rules and standards from the tech spec",
            required=True,
            example="- Use type hints\n- Write docstrings\n...",
        ),
        TemplateVariable(
            name="batch_name",
            description="Name of the current implementation batch",
            required=True,
            example="models",
        ),
        TemplateVariable(
            name="batch_scope",
            description="Scope of files/features in this batch",
            required=True,
            example="Implement data models in src/models/",
        ),
    ],
    "qa": [
        TemplateVariable(
            name="acceptance_criteria",
            description="Acceptance criteria extracted from the PRD",
            required=True,
            example="Given a user, when they log in, then show dashboard",
        ),
    ],
}


class PromptTemplateManager:
    """Manages prompt templates for persona system prompts.

    This class provides functionality to:
    - Load prompt templates from markdown files
    - Render templates with context variables
    - Validate templates for completeness
    - Track template versions

    Example:
        >>> manager = PromptTemplateManager()
        >>> prompt = manager.render_template("pm", {"user_mission": "Build an app"})
        >>> print(prompt[:50])
    """

    # Default templates directory
    DEFAULT_TEMPLATES_DIR: ClassVar[Path] = Path(__file__).parent

    # Valid personas
    VALID_PERSONAS: ClassVar[list[str]] = ["pm", "arch", "eng", "qa"]

    # Mapping from persona short name to template file name
    PERSONA_FILE_MAP: ClassVar[dict[str, str]] = {
        "pm": "pm_prompt.md",
        "arch": "architect_prompt.md",
        "eng": "engineer_prompt.md",
        "qa": "qa_prompt.md",
    }

    def __init__(
        self,
        templates_dir: Path | None = None,
        strict_mode: bool = True,
    ) -> None:
        """Initialize the template manager.

        Args:
            templates_dir: Directory containing template files.
            strict_mode: If True, raise errors on undefined variables.
        """
        self.templates_dir = templates_dir or self.DEFAULT_TEMPLATES_DIR
        self.strict_mode = strict_mode

        # Set up Jinja2 environment
        # Use {{ }} for Jinja2 and { } for simple replacement
        self._env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            undefined=StrictUndefined if strict_mode else Undefined,
            autoescape=False,  # Markdown doesn't need escaping
            keep_trailing_newline=True,
        )

        # Cache for loaded templates
        self._template_cache: dict[str, Template] = {}
        self._metadata_cache: dict[str, TemplateMetadata] = {}

    def _get_template_path(self, persona: str) -> Path:
        """Get the file path for a persona's template.

        Args:
            persona: The persona name.

        Returns:
            Path to the template file.

        Raises:
            ValueError: If persona is invalid.
        """
        if persona not in self.VALID_PERSONAS:
            raise ValueError(
                f"Invalid persona '{persona}'. "
                f"Valid personas: {', '.join(self.VALID_PERSONAS)}"
            )
        return self.templates_dir / self.PERSONA_FILE_MAP[persona]

    def load_template(self, persona: str) -> str:
        """Load the raw template content for a persona.

        Args:
            persona: The persona name (pm, arch, eng, qa).

        Returns:
            The raw template content.

        Raises:
            TemplateNotFoundError: If template file doesn't exist.
        """
        template_path = self._get_template_path(persona)

        if not template_path.exists():
            raise TemplateNotFoundError(
                f"Template not found for persona '{persona}': {template_path}"
            )

        return template_path.read_text(encoding="utf-8")

    def render_template(
        self,
        persona: str,
        context: dict[str, Any],
    ) -> str:
        """Render a template with the given context.

        This method uses simple string replacement for {variable} placeholders
        to maintain compatibility with existing templates.

        Args:
            persona: The persona name.
            context: Dictionary of variables to substitute.

        Returns:
            The rendered template.

        Raises:
            TemplateNotFoundError: If template doesn't exist.
            TemplateRenderError: If rendering fails (missing variables in strict mode).
        """
        template_content = self.load_template(persona)

        # Find all placeholders in the template
        placeholders = self._extract_placeholders(template_content)

        # Check for missing required variables in strict mode
        if self.strict_mode:
            missing = placeholders - set(context.keys())
            if missing:
                raise TemplateRenderError(
                    f"Missing required variables for '{persona}' template: {missing}"
                )

        # Perform simple string replacement
        rendered = template_content
        for key, value in context.items():
            placeholder = "{" + key + "}"
            if placeholder in rendered:
                rendered = rendered.replace(placeholder, str(value))

        return rendered

    def render_template_jinja(
        self,
        persona: str,
        context: dict[str, Any],
    ) -> str:
        """Render a template using Jinja2 syntax.

        Use this for templates that use {{ variable }} Jinja2 syntax.

        Args:
            persona: The persona name.
            context: Dictionary of variables to substitute.

        Returns:
            The rendered template.

        Raises:
            TemplateNotFoundError: If template doesn't exist.
            TemplateRenderError: If rendering fails.
        """
        template_name = self.PERSONA_FILE_MAP[persona]

        try:
            template = self._env.get_template(template_name)
            return template.render(**context)
        except UndefinedError as e:
            raise TemplateRenderError(
                f"Missing variable in '{persona}' template: {e}"
            ) from e
        except TemplateSyntaxError as e:
            raise TemplateRenderError(
                f"Syntax error in '{persona}' template: {e}"
            ) from e

    def validate_template(
        self,
        persona: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Validate a template for completeness and correctness.

        Args:
            persona: The persona name.
            context: Optional context to check against.

        Returns:
            ValidationResult with any errors/warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []
        missing_vars: list[str] = []
        unused_vars: list[str] = []

        # Check template exists
        try:
            content = self.load_template(persona)
        except TemplateNotFoundError as e:
            return ValidationResult(
                is_valid=False,
                errors=[str(e)],
            )

        # Extract placeholders from template
        template_vars = self._extract_placeholders(content)

        # Get expected variables for this persona
        expected_vars = PERSONA_VARIABLES.get(persona, [])
        expected_names = {v.name for v in expected_vars}

        # Check for missing expected variables in template
        for var in expected_vars:
            if var.name not in template_vars:
                if var.required:
                    errors.append(
                        f"Required variable '{var.name}' not found in template"
                    )
                else:
                    warnings.append(
                        f"Optional variable '{var.name}' not found in template"
                    )

        # Check for unknown variables in template
        unknown_vars = template_vars - expected_names
        if unknown_vars:
            warnings.append(
                f"Unknown variables in template: {unknown_vars}"
            )

        # If context provided, check for completeness
        if context is not None:
            context_vars = set(context.keys())

            # Variables in template but not in context
            missing_vars = list(template_vars - context_vars)
            if missing_vars:
                errors.append(
                    f"Context missing required variables: {missing_vars}"
                )

            # Variables in context but not in template
            unused_vars = list(context_vars - template_vars)
            if unused_vars:
                warnings.append(
                    f"Context has unused variables: {unused_vars}"
                )

        # Validate Markdown syntax
        md_errors, md_warnings = self._validate_markdown(content)
        errors.extend(md_errors)
        warnings.extend(md_warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            missing_variables=missing_vars,
            unused_variables=unused_vars,
        )

    def _extract_placeholders(self, content: str) -> set[str]:
        """Extract placeholder variable names from template content.

        Placeholders in fenced code blocks (```...```) are excluded since they
        are typically code examples, not actual template variables.

        Args:
            content: The template content.

        Returns:
            Set of variable names found in {variable} placeholders.
        """
        # Remove fenced code blocks to avoid matching placeholders in code examples
        # These are typically multi-line code snippets, not template variables
        content_no_code = re.sub(r"```[\s\S]*?```", "", content)

        # Match {variable_name} but not {{ or }}
        pattern = r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})"
        matches = re.findall(pattern, content_no_code)
        return set(matches)

    def _validate_markdown(self, content: str) -> tuple[list[str], list[str]]:
        """Validate Markdown syntax in template content.

        Args:
            content: The template content.

        Returns:
            Tuple of (errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check for unclosed code blocks - this is an error
        code_block_count = content.count("```")
        if code_block_count % 2 != 0:
            errors.append("Unclosed code block (``` count is odd)")

        # Check for proper heading hierarchy - these are warnings, not errors
        # Existing templates may have valid reasons for heading patterns
        headings = re.findall(r"^(#+)\s+\S", content, re.MULTILINE)
        if headings:
            levels = [len(h) for h in headings]
            # First heading should be level 1 or 2
            if levels[0] > 2:
                warnings.append(f"First heading should be level 1 or 2, found level {levels[0]}")
            # No more than one level jump
            for i in range(1, len(levels)):
                if levels[i] > levels[i - 1] + 1:
                    warnings.append(
                        f"Heading level jumps from {levels[i-1]} to {levels[i]} at heading {i+1}"
                    )

        return errors, warnings

    def get_template_metadata(self, persona: str) -> TemplateMetadata:
        """Get metadata for a template.

        Args:
            persona: The persona name.

        Returns:
            TemplateMetadata with version and variable info.
        """
        if persona in self._metadata_cache:
            return self._metadata_cache[persona]

        template_path = self._get_template_path(persona)
        content = self.load_template(persona)

        # Calculate content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]

        # Try to get git version
        version = self._get_git_version(template_path) or content_hash

        # Get last modified time
        last_modified = None
        if template_path.exists():
            mtime = template_path.stat().st_mtime
            last_modified = datetime.fromtimestamp(mtime)

        # Get expected variables
        variables = PERSONA_VARIABLES.get(persona, [])

        metadata = TemplateMetadata(
            persona=persona,
            version=version,
            variables=variables,
            last_modified=last_modified,
            file_path=template_path,
            content_hash=content_hash,
        )

        self._metadata_cache[persona] = metadata
        return metadata

    def _get_git_version(self, file_path: Path) -> str | None:
        """Get the git version (short commit hash) for a file.

        Args:
            file_path: Path to the file.

        Returns:
            Short git commit hash or None if not in git.
        """
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%h", str(file_path)],
                capture_output=True,
                text=True,
                cwd=file_path.parent,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def get_template_history(self, persona: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get git history for a template file.

        Args:
            persona: The persona name.
            limit: Maximum number of commits to return.

        Returns:
            List of commit info dictionaries.
        """
        template_path = self._get_template_path(persona)
        history: list[dict[str, Any]] = []

        try:
            result = subprocess.run(
                [
                    "git", "log",
                    f"-{limit}",
                    "--format=%H|%h|%an|%ai|%s",
                    str(template_path),
                ],
                capture_output=True,
                text=True,
                cwd=template_path.parent,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split("|")
                        if len(parts) >= 5:
                            history.append({
                                "commit_hash": parts[0],
                                "short_hash": parts[1],
                                "author": parts[2],
                                "date": parts[3],
                                "message": parts[4],
                            })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return history

    def list_templates(self) -> list[TemplateMetadata]:
        """List all available templates with metadata.

        Returns:
            List of TemplateMetadata for all templates.
        """
        return [self.get_template_metadata(persona) for persona in self.VALID_PERSONAS]

    def get_required_variables(self, persona: str) -> list[str]:
        """Get list of required variables for a persona.

        Args:
            persona: The persona name.

        Returns:
            List of required variable names.
        """
        variables = PERSONA_VARIABLES.get(persona, [])
        return [v.name for v in variables if v.required]

    def get_variable_documentation(self, persona: str) -> str:
        """Generate documentation for template variables.

        Args:
            persona: The persona name.

        Returns:
            Markdown documentation string.
        """
        variables = PERSONA_VARIABLES.get(persona, [])
        if not variables:
            return f"No documented variables for persona '{persona}'."

        lines = [
            f"# Template Variables for {persona.upper()}",
            "",
            "| Variable | Required | Description | Example |",
            "|----------|----------|-------------|---------|",
        ]

        for var in variables:
            required = "Yes" if var.required else "No"
            example = var.example[:50] + "..." if var.example and len(var.example) > 50 else (var.example or "")
            lines.append(f"| `{var.name}` | {required} | {var.description} | {example} |")

        return "\n".join(lines)

    def clear_cache(self) -> None:
        """Clear the template and metadata caches."""
        self._template_cache.clear()
        self._metadata_cache.clear()


def validate_all_templates(
    templates_dir: Path | None = None,
) -> dict[str, ValidationResult]:
    """Validate all persona templates.

    Args:
        templates_dir: Optional templates directory.

    Returns:
        Dictionary mapping persona names to validation results.
    """
    manager = PromptTemplateManager(templates_dir=templates_dir, strict_mode=False)
    return {
        persona: manager.validate_template(persona)
        for persona in manager.VALID_PERSONAS
    }


def main() -> None:
    """CLI entry point for template management."""
    import argparse

    parser = argparse.ArgumentParser(description="Prompt Template Manager")
    parser.add_argument(
        "--validate",
        type=str,
        metavar="PERSONA",
        help="Validate a specific template (pm, arch, eng, qa)",
    )
    parser.add_argument(
        "--validate-all",
        action="store_true",
        help="Validate all templates",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all templates with metadata",
    )
    parser.add_argument(
        "--history",
        type=str,
        metavar="PERSONA",
        help="Show git history for a template",
    )
    parser.add_argument(
        "--vars",
        type=str,
        metavar="PERSONA",
        help="Show variable documentation for a template",
    )

    args = parser.parse_args()
    manager = PromptTemplateManager(strict_mode=False)

    if args.validate:
        result = manager.validate_template(args.validate)
        print(f"Validation for '{args.validate}':")
        print(f"  Valid: {result.is_valid}")
        if result.errors:
            print(f"  Errors: {result.errors}")
        if result.warnings:
            print(f"  Warnings: {result.warnings}")

    elif args.validate_all:
        results = validate_all_templates()
        all_valid = True
        for persona, result in results.items():
            status = "PASS" if result.is_valid else "FAIL"
            print(f"  {persona}: {status}")
            if not result.is_valid:
                all_valid = False
                for error in result.errors:
                    print(f"    - {error}")
        print(f"\nOverall: {'PASS' if all_valid else 'FAIL'}")

    elif args.list:
        templates = manager.list_templates()
        print("Available Templates:")
        print("-" * 60)
        for meta in templates:
            print(f"  {meta.persona}:")
            print(f"    File: {meta.file_path}")
            print(f"    Version: {meta.version}")
            print(f"    Variables: {[v.name for v in meta.variables]}")
            if meta.last_modified:
                print(f"    Modified: {meta.last_modified.isoformat()}")
            print()

    elif args.history:
        history = manager.get_template_history(args.history)
        if history:
            print(f"Git history for '{args.history}' template:")
            for commit in history:
                print(f"  {commit['short_hash']} - {commit['message']} ({commit['date'][:10]})")
        else:
            print(f"No git history found for '{args.history}'")

    elif args.vars:
        doc = manager.get_variable_documentation(args.vars)
        print(doc)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
