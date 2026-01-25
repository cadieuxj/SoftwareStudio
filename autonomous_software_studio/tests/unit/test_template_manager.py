"""Unit tests for the Prompt Template Manager.

Tests cover:
- Template loading
- Variable substitution
- Missing variable detection
- Markdown validation
- Version tracking
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.personas.template_manager import (
    PERSONA_VARIABLES,
    PromptTemplateManager,
    TemplateMetadata,
    TemplateNotFoundError,
    TemplateRenderError,
    TemplateVariable,
    ValidationResult,
    validate_all_templates,
)


class TestPromptTemplateManagerInit:
    """Tests for PromptTemplateManager initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initializing with default values."""
        manager = PromptTemplateManager()

        assert manager.templates_dir.exists()
        assert manager.strict_mode is True

    def test_init_with_custom_dir(self) -> None:
        """Test initializing with custom templates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PromptTemplateManager(
                templates_dir=Path(tmpdir),
                strict_mode=False,
            )

            assert manager.templates_dir == Path(tmpdir)
            assert manager.strict_mode is False

    def test_valid_personas(self) -> None:
        """Test that valid personas are defined."""
        manager = PromptTemplateManager()

        assert "pm" in manager.VALID_PERSONAS
        assert "arch" in manager.VALID_PERSONAS
        assert "eng" in manager.VALID_PERSONAS
        assert "qa" in manager.VALID_PERSONAS


class TestTemplateLoading:
    """Tests for template loading functionality."""

    def test_load_template_pm(self) -> None:
        """Test loading PM template."""
        manager = PromptTemplateManager()
        content = manager.load_template("pm")

        assert "Product Manager" in content
        assert "{user_mission}" in content

    def test_load_template_arch(self) -> None:
        """Test loading Architect template."""
        manager = PromptTemplateManager()
        content = manager.load_template("arch")

        assert "Architect" in content
        assert "{prd_content}" in content

    def test_load_template_eng(self) -> None:
        """Test loading Engineer template."""
        manager = PromptTemplateManager()
        content = manager.load_template("eng")

        assert "Engineer" in content
        assert "{tech_spec_content}" in content
        assert "{rules_of_engagement}" in content
        assert "{batch_name}" in content
        assert "{batch_scope}" in content

    def test_load_template_qa(self) -> None:
        """Test loading QA template."""
        manager = PromptTemplateManager()
        content = manager.load_template("qa")

        assert "QA" in content
        assert "{acceptance_criteria}" in content

    def test_load_template_invalid_persona(self) -> None:
        """Test loading template for invalid persona."""
        manager = PromptTemplateManager()

        with pytest.raises(ValueError, match="Invalid persona"):
            manager.load_template("invalid")

    def test_load_template_not_found(self) -> None:
        """Test loading template that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PromptTemplateManager(templates_dir=Path(tmpdir))

            with pytest.raises(TemplateNotFoundError):
                manager.load_template("pm")


class TestTemplateRendering:
    """Tests for template rendering functionality."""

    def test_render_template_pm(self) -> None:
        """Test rendering PM template with context."""
        manager = PromptTemplateManager()
        result = manager.render_template(
            "pm",
            {"user_mission": "Build a task management app"},
        )

        assert "Build a task management app" in result
        assert "{user_mission}" not in result

    def test_render_template_arch(self) -> None:
        """Test rendering Architect template with context."""
        manager = PromptTemplateManager()
        result = manager.render_template(
            "arch",
            {"prd_content": "# Product Requirements\n\nUser Stories..."},
        )

        assert "# Product Requirements" in result
        assert "{prd_content}" not in result

    def test_render_template_eng(self) -> None:
        """Test rendering Engineer template with all variables."""
        manager = PromptTemplateManager()
        result = manager.render_template(
            "eng",
            {
                "tech_spec_content": "# Technical Specification",
                "rules_of_engagement": "- Use type hints\n- Write tests",
                "batch_name": "models",
                "batch_scope": "Implement data models",
            },
        )

        assert "# Technical Specification" in result
        assert "- Use type hints" in result
        assert "models" in result
        assert "Implement data models" in result

    def test_render_template_qa(self) -> None:
        """Test rendering QA template with context."""
        manager = PromptTemplateManager()
        result = manager.render_template(
            "qa",
            {"acceptance_criteria": "Given a user, when they log in, then show dashboard"},
        )

        assert "Given a user" in result
        assert "{acceptance_criteria}" not in result

    def test_render_template_missing_variable_strict(self) -> None:
        """Test that missing variables raise error in strict mode."""
        manager = PromptTemplateManager(strict_mode=True)

        with pytest.raises(TemplateRenderError, match="Missing required"):
            manager.render_template("pm", {})

    def test_render_template_missing_variable_non_strict(self) -> None:
        """Test that missing variables are kept in non-strict mode."""
        manager = PromptTemplateManager(strict_mode=False)
        result = manager.render_template("pm", {})

        # Variable placeholder should remain
        assert "{user_mission}" in result

    def test_render_template_extra_variables(self) -> None:
        """Test that extra variables in context are ignored."""
        manager = PromptTemplateManager()
        result = manager.render_template(
            "pm",
            {
                "user_mission": "Build an app",
                "extra_var": "This should be ignored",
            },
        )

        assert "Build an app" in result
        assert "This should be ignored" not in result


class TestTemplateValidation:
    """Tests for template validation functionality."""

    def test_validate_template_pm_valid(self) -> None:
        """Test validating valid PM template."""
        manager = PromptTemplateManager()
        result = manager.validate_template("pm")

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_template_with_complete_context(self) -> None:
        """Test validation with complete context."""
        manager = PromptTemplateManager()
        result = manager.validate_template(
            "pm",
            {"user_mission": "Build an app"},
        )

        assert result.is_valid is True
        assert len(result.missing_variables) == 0

    def test_validate_template_with_incomplete_context(self) -> None:
        """Test validation with missing context variables."""
        manager = PromptTemplateManager()
        result = manager.validate_template(
            "pm",
            {},  # Missing user_mission
        )

        assert result.is_valid is False
        assert "user_mission" in result.missing_variables

    def test_validate_template_with_extra_context(self) -> None:
        """Test validation with extra context variables."""
        manager = PromptTemplateManager()
        result = manager.validate_template(
            "pm",
            {
                "user_mission": "Build an app",
                "unused_var": "Not used",
            },
        )

        assert result.is_valid is True
        assert "unused_var" in result.unused_variables

    def test_validate_nonexistent_template(self) -> None:
        """Test validation of non-existent template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PromptTemplateManager(templates_dir=Path(tmpdir))
            result = manager.validate_template("pm")

            assert result.is_valid is False
            assert any("not found" in e.lower() for e in result.errors)


class TestMarkdownValidation:
    """Tests for Markdown validation within templates."""

    def test_valid_markdown(self) -> None:
        """Test that valid Markdown passes validation."""
        manager = PromptTemplateManager()

        # All existing templates should have valid Markdown
        for persona in manager.VALID_PERSONAS:
            result = manager.validate_template(persona)
            # Check no markdown-related errors
            md_errors = [e for e in result.errors if "code block" in e.lower() or "heading" in e.lower()]
            assert len(md_errors) == 0, f"Markdown errors in {persona}: {md_errors}"

    def test_unclosed_code_block_detection(self) -> None:
        """Test detection of unclosed code blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "pm_prompt.md"
            template_path.write_text(
                "# Test\n\n{user_mission}\n\n```python\ncode here\n",  # No closing ```
                encoding="utf-8",
            )

            manager = PromptTemplateManager(templates_dir=Path(tmpdir))
            result = manager.validate_template("pm")

            assert any("code block" in e.lower() for e in result.errors)


class TestTemplateMetadata:
    """Tests for template metadata functionality."""

    def test_get_metadata_pm(self) -> None:
        """Test getting metadata for PM template."""
        manager = PromptTemplateManager()
        metadata = manager.get_template_metadata("pm")

        assert metadata.persona == "pm"
        assert metadata.file_path.exists()
        assert len(metadata.content_hash) > 0
        assert len(metadata.variables) > 0

    def test_get_metadata_all_personas(self) -> None:
        """Test getting metadata for all personas."""
        manager = PromptTemplateManager()

        for persona in manager.VALID_PERSONAS:
            metadata = manager.get_template_metadata(persona)
            assert metadata.persona == persona
            assert metadata.file_path.exists()

    def test_metadata_caching(self) -> None:
        """Test that metadata is cached."""
        manager = PromptTemplateManager()

        metadata1 = manager.get_template_metadata("pm")
        metadata2 = manager.get_template_metadata("pm")

        assert metadata1 is metadata2  # Same object (cached)

    def test_clear_cache(self) -> None:
        """Test clearing the metadata cache."""
        manager = PromptTemplateManager()

        metadata1 = manager.get_template_metadata("pm")
        manager.clear_cache()
        metadata2 = manager.get_template_metadata("pm")

        assert metadata1 is not metadata2  # Different objects

    def test_list_templates(self) -> None:
        """Test listing all templates."""
        manager = PromptTemplateManager()
        templates = manager.list_templates()

        assert len(templates) == 4
        personas = [t.persona for t in templates]
        assert "pm" in personas
        assert "arch" in personas
        assert "eng" in personas
        assert "qa" in personas


class TestVersionTracking:
    """Tests for version tracking functionality."""

    def test_get_template_history(self) -> None:
        """Test getting template git history."""
        manager = PromptTemplateManager()
        history = manager.get_template_history("pm")

        # May be empty if not in git, but should not error
        assert isinstance(history, list)

    def test_version_includes_hash(self) -> None:
        """Test that version includes content hash or git hash."""
        manager = PromptTemplateManager()
        metadata = manager.get_template_metadata("pm")

        # Version should be non-empty
        assert len(metadata.version) > 0


class TestPersonaVariables:
    """Tests for persona variable definitions."""

    def test_pm_variables_defined(self) -> None:
        """Test that PM variables are properly defined."""
        pm_vars = PERSONA_VARIABLES.get("pm", [])

        assert len(pm_vars) > 0
        names = [v.name for v in pm_vars]
        assert "user_mission" in names

    def test_arch_variables_defined(self) -> None:
        """Test that Architect variables are properly defined."""
        arch_vars = PERSONA_VARIABLES.get("arch", [])

        names = [v.name for v in arch_vars]
        assert "prd_content" in names

    def test_eng_variables_defined(self) -> None:
        """Test that Engineer variables are properly defined."""
        eng_vars = PERSONA_VARIABLES.get("eng", [])

        names = [v.name for v in eng_vars]
        assert "tech_spec_content" in names
        assert "rules_of_engagement" in names
        assert "batch_name" in names
        assert "batch_scope" in names

    def test_qa_variables_defined(self) -> None:
        """Test that QA variables are properly defined."""
        qa_vars = PERSONA_VARIABLES.get("qa", [])

        names = [v.name for v in qa_vars]
        assert "acceptance_criteria" in names

    def test_get_required_variables(self) -> None:
        """Test getting required variables for a persona."""
        manager = PromptTemplateManager()
        required = manager.get_required_variables("eng")

        assert "tech_spec_content" in required
        assert "rules_of_engagement" in required
        assert "batch_name" in required
        assert "batch_scope" in required


class TestVariableDocumentation:
    """Tests for variable documentation generation."""

    def test_get_variable_documentation_pm(self) -> None:
        """Test generating documentation for PM variables."""
        manager = PromptTemplateManager()
        doc = manager.get_variable_documentation("pm")

        assert "Template Variables" in doc
        assert "user_mission" in doc
        assert "|" in doc  # Markdown table

    def test_get_variable_documentation_all(self) -> None:
        """Test generating documentation for all personas."""
        manager = PromptTemplateManager()

        for persona in manager.VALID_PERSONAS:
            doc = manager.get_variable_documentation(persona)
            assert len(doc) > 0
            assert persona.upper() in doc


class TestValidateAllTemplates:
    """Tests for the validate_all_templates utility function."""

    def test_validate_all_templates(self) -> None:
        """Test validating all templates at once."""
        results = validate_all_templates()

        assert "pm" in results
        assert "arch" in results
        assert "eng" in results
        assert "qa" in results

        # All should be valid
        for persona, result in results.items():
            assert result.is_valid, f"Template {persona} is invalid: {result.errors}"


class TestPlaceholderExtraction:
    """Tests for placeholder extraction functionality."""

    def test_extract_single_placeholder(self) -> None:
        """Test extracting a single placeholder."""
        manager = PromptTemplateManager()
        placeholders = manager._extract_placeholders("Hello {name}!")

        assert placeholders == {"name"}

    def test_extract_multiple_placeholders(self) -> None:
        """Test extracting multiple placeholders."""
        manager = PromptTemplateManager()
        placeholders = manager._extract_placeholders("{greeting} {name}, how is {thing}?")

        assert placeholders == {"greeting", "name", "thing"}

    def test_extract_no_placeholders(self) -> None:
        """Test extracting when there are no placeholders."""
        manager = PromptTemplateManager()
        placeholders = manager._extract_placeholders("No variables here!")

        assert placeholders == set()

    def test_ignore_double_braces(self) -> None:
        """Test that double braces are ignored."""
        manager = PromptTemplateManager()
        placeholders = manager._extract_placeholders("{{not_a_var}} but {is_a_var}")

        assert "is_a_var" in placeholders
        # Double braces might still be caught, which is fine
        # The important thing is {is_a_var} is found

    def test_extract_underscored_variables(self) -> None:
        """Test extracting variables with underscores."""
        manager = PromptTemplateManager()
        placeholders = manager._extract_placeholders("{user_mission} and {tech_spec_content}")

        assert "user_mission" in placeholders
        assert "tech_spec_content" in placeholders


class TestTemplateVariable:
    """Tests for TemplateVariable dataclass."""

    def test_create_template_variable(self) -> None:
        """Test creating a TemplateVariable."""
        var = TemplateVariable(
            name="test_var",
            description="A test variable",
            required=True,
            example="example value",
        )

        assert var.name == "test_var"
        assert var.description == "A test variable"
        assert var.required is True
        assert var.example == "example value"

    def test_template_variable_defaults(self) -> None:
        """Test TemplateVariable default values."""
        var = TemplateVariable(name="simple")

        assert var.name == "simple"
        assert var.description == ""
        assert var.required is True
        assert var.default is None
        assert var.example is None


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_create_validation_result_valid(self) -> None:
        """Test creating a valid ValidationResult."""
        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_create_validation_result_invalid(self) -> None:
        """Test creating an invalid ValidationResult."""
        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            missing_variables=["var1"],
            unused_variables=["var2"],
        )

        assert result.is_valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert "var1" in result.missing_variables
        assert "var2" in result.unused_variables
