"""Unit tests for the Context Manager.

Tests cover:
- Context generation for each phase
- Rule appending maintains order
- File size limit enforcement
- Backup creation on update
- UTF-8 encoding preservation
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from src.orchestration.context_manager import (
    MAX_CONTEXT_SIZE,
    ContextError,
    ContextManager,
    ContextSizeExceededError,
    PhaseContext,
    generate_sample_contexts,
)


class TestPhaseContext:
    """Tests for the PhaseContext dataclass."""

    def test_phase_context_creation(self) -> None:
        """Test creating a PhaseContext with default values."""
        ctx = PhaseContext(phase_name="pm")

        assert ctx.phase_name == "pm"
        assert ctx.mission == ""
        assert ctx.guidelines == []
        assert ctx.artifacts == []
        assert ctx.rules == []
        assert ctx.metadata == {}

    def test_phase_context_with_all_fields(self) -> None:
        """Test creating a PhaseContext with all fields populated."""
        ctx = PhaseContext(
            phase_name="arch",
            mission="Build a great app",
            guidelines=["Design first", "Document decisions"],
            artifacts=["prd.md"],
            rules=["Follow patterns"],
            metadata={"priority": "high"},
        )

        assert ctx.phase_name == "arch"
        assert ctx.mission == "Build a great app"
        assert len(ctx.guidelines) == 2
        assert len(ctx.artifacts) == 1
        assert len(ctx.rules) == 1
        assert ctx.metadata["priority"] == "high"


class TestContextManager:
    """Tests for the ContextManager class."""

    def test_manager_initialization(self) -> None:
        """Test ContextManager initialization."""
        manager = ContextManager()

        assert manager._current_context is None
        assert manager._version == 0
        assert manager._custom_rules == []

    def test_manager_with_custom_backup_dir(self, tmp_path: Path) -> None:
        """Test manager with custom backup directory."""
        backup_dir = tmp_path / "custom_backups"
        manager = ContextManager(backup_dir=backup_dir)

        assert manager._backup_dir == backup_dir

    def test_manager_with_custom_max_size(self) -> None:
        """Test manager with custom max size."""
        manager = ContextManager(max_size=1024)

        assert manager._max_size == 1024

    def test_update_context_valid_phase(self) -> None:
        """Test updating context with valid phase."""
        manager = ContextManager()

        manager.update_context("pm", {"mission": "Build task app"})

        assert manager._current_context is not None
        assert manager._current_context.phase_name == "pm"
        assert manager._current_context.mission == "Build task app"
        assert manager._version == 1

    def test_update_context_case_insensitive(self) -> None:
        """Test that phase names are case insensitive."""
        manager = ContextManager()

        manager.update_context("PM", {"mission": "Test"})
        assert manager._current_context is not None
        assert manager._current_context.phase_name == "pm"

        manager.update_context("Arch", {"mission": "Test"})
        assert manager._current_context.phase_name == "arch"

    def test_update_context_invalid_phase(self) -> None:
        """Test updating context with invalid phase raises error."""
        manager = ContextManager()

        with pytest.raises(ContextError, match="Invalid phase"):
            manager.update_context("invalid", {"mission": "Test"})

    def test_update_context_uses_defaults(self) -> None:
        """Test that update_context uses default guidelines if not provided."""
        manager = ContextManager()

        manager.update_context("pm", {"mission": "Test"})

        assert manager._current_context is not None
        assert len(manager._current_context.guidelines) > 0
        assert len(manager._current_context.rules) > 0

    def test_update_context_custom_overrides_defaults(self) -> None:
        """Test that custom content overrides defaults."""
        manager = ContextManager()

        custom_guidelines = ["Custom guideline 1", "Custom guideline 2"]
        manager.update_context(
            "pm",
            {
                "mission": "Test",
                "guidelines": custom_guidelines,
            },
        )

        assert manager._current_context is not None
        assert manager._current_context.guidelines == custom_guidelines

    def test_update_context_increments_version(self) -> None:
        """Test that each update increments version."""
        manager = ContextManager()

        manager.update_context("pm", {"mission": "Test 1"})
        assert manager._version == 1

        manager.update_context("arch", {"mission": "Test 2"})
        assert manager._version == 2

        manager.update_context("eng", {"mission": "Test 3"})
        assert manager._version == 3


class TestGenerateClaudeMd:
    """Tests for CLAUDE.md generation."""

    def test_generate_without_context_raises_error(self, tmp_path: Path) -> None:
        """Test that generating without context raises error."""
        manager = ContextManager()

        with pytest.raises(ContextError, match="No context set"):
            manager.generate_claude_md(tmp_path)

    def test_generate_creates_file(self, tmp_path: Path) -> None:
        """Test that generate creates CLAUDE.md file."""
        manager = ContextManager()
        manager.update_context("pm", {"mission": "Test project"})

        path = manager.generate_claude_md(tmp_path)

        assert path.exists()
        assert path.name == "CLAUDE.md"

    def test_generate_creates_directory_if_missing(self, tmp_path: Path) -> None:
        """Test that generate creates work directory if missing."""
        manager = ContextManager()
        manager.update_context("pm", {"mission": "Test"})

        new_dir = tmp_path / "new" / "nested" / "dir"
        path = manager.generate_claude_md(new_dir)

        assert new_dir.exists()
        assert path.exists()

    def test_generate_content_includes_phase(self, tmp_path: Path) -> None:
        """Test that generated content includes phase name."""
        manager = ContextManager()
        manager.update_context("arch", {"mission": "Test"})

        path = manager.generate_claude_md(tmp_path)
        content = path.read_text()

        assert "Architect" in content
        assert "Current Phase" in content

    def test_generate_content_includes_mission(self, tmp_path: Path) -> None:
        """Test that generated content includes mission."""
        manager = ContextManager()
        manager.update_context("pm", {"mission": "Build amazing software"})

        path = manager.generate_claude_md(tmp_path)
        content = path.read_text()

        assert "Build amazing software" in content
        assert "Project Mission" in content

    def test_generate_content_includes_guidelines(self, tmp_path: Path) -> None:
        """Test that generated content includes guidelines."""
        manager = ContextManager()
        manager.update_context(
            "eng",
            {
                "mission": "Test",
                "guidelines": ["Guideline 1", "Guideline 2"],
            },
        )

        path = manager.generate_claude_md(tmp_path)
        content = path.read_text()

        assert "Guideline 1" in content
        assert "Guideline 2" in content
        assert "Phase-Specific Guidelines" in content

    def test_generate_content_includes_artifacts(self, tmp_path: Path) -> None:
        """Test that generated content includes artifacts."""
        manager = ContextManager()
        manager.update_context(
            "qa",
            {
                "mission": "Test",
                "artifacts": ["prd.md", "architecture.md"],
            },
        )

        path = manager.generate_claude_md(tmp_path)
        content = path.read_text()

        assert "prd.md" in content
        assert "architecture.md" in content
        assert "Artifacts Available" in content

    def test_generate_content_includes_rules(self, tmp_path: Path) -> None:
        """Test that generated content includes rules."""
        manager = ContextManager()
        manager.update_context(
            "pm",
            {
                "mission": "Test",
                "rules": ["Rule 1", "Rule 2"],
            },
        )

        path = manager.generate_claude_md(tmp_path)
        content = path.read_text()

        assert "Rule 1" in content
        assert "Rule 2" in content
        assert "Rules of Engagement" in content

    def test_generate_content_includes_metadata(self, tmp_path: Path) -> None:
        """Test that generated content includes metadata."""
        manager = ContextManager()
        manager.update_context(
            "pm",
            {
                "mission": "Test",
                "metadata": {"priority": "high", "deadline": "2024-01-01"},
            },
        )

        path = manager.generate_claude_md(tmp_path)
        content = path.read_text()

        assert "priority" in content
        assert "high" in content
        assert "Additional Context" in content

    def test_generate_includes_version(self, tmp_path: Path) -> None:
        """Test that generated content includes version."""
        manager = ContextManager()
        manager.update_context("pm", {"mission": "Test"})
        manager.update_context("arch", {"mission": "Test 2"})

        path = manager.generate_claude_md(tmp_path)
        content = path.read_text()

        assert "Version 2" in content

    def test_generate_utf8_encoding(self, tmp_path: Path) -> None:
        """Test that content is UTF-8 encoded."""
        manager = ContextManager()
        manager.update_context(
            "pm",
            {
                "mission": "Test with special chars: \u00e9\u00e8\u00ea \u4e2d\u6587 \U0001f600",
            },
        )

        path = manager.generate_claude_md(tmp_path)
        content = path.read_text(encoding="utf-8")

        assert "\u00e9\u00e8\u00ea" in content
        assert "\u4e2d\u6587" in content
        assert "\U0001f600" in content


class TestFileSizeLimit:
    """Tests for file size limit enforcement."""

    def test_size_limit_warning(self, tmp_path: Path) -> None:
        """Test that exceeding size limit raises error."""
        # Create manager with very small limit
        manager = ContextManager(max_size=100)
        manager.update_context(
            "pm",
            {
                "mission": "A" * 200,  # Exceed the limit
            },
        )

        with pytest.raises(ContextSizeExceededError, match="exceeds limit"):
            manager.generate_claude_md(tmp_path)

    def test_within_size_limit_succeeds(self, tmp_path: Path) -> None:
        """Test that content within limit succeeds."""
        manager = ContextManager(max_size=MAX_CONTEXT_SIZE)
        manager.update_context("pm", {"mission": "Short mission"})

        path = manager.generate_claude_md(tmp_path)
        assert path.exists()

        # Verify size is within limit
        size = path.stat().st_size
        assert size < MAX_CONTEXT_SIZE


class TestBackupSystem:
    """Tests for the backup system."""

    def test_backup_created_on_update(self, tmp_path: Path) -> None:
        """Test that backup is created when updating existing file."""
        backup_dir = tmp_path / "backups"
        manager = ContextManager(backup_dir=backup_dir)

        # Create initial file
        manager.update_context("pm", {"mission": "Version 1"})
        manager.generate_claude_md(tmp_path)

        # Update with new content (should create backup)
        manager.update_context("arch", {"mission": "Version 2"})
        manager.generate_claude_md(tmp_path)

        # Check backup was created
        assert backup_dir.exists()
        backups = list(backup_dir.glob("CLAUDE_*.md"))
        assert len(backups) == 1

    def test_backup_contains_original_content(self, tmp_path: Path) -> None:
        """Test that backup contains original content."""
        backup_dir = tmp_path / "backups"
        manager = ContextManager(backup_dir=backup_dir)

        # Create initial file
        manager.update_context("pm", {"mission": "Original content"})
        manager.generate_claude_md(tmp_path)

        # Update
        manager.update_context("arch", {"mission": "New content"})
        manager.generate_claude_md(tmp_path)

        # Check backup content
        backups = list(backup_dir.glob("CLAUDE_*.md"))
        backup_content = backups[0].read_text()
        assert "Original content" in backup_content


class TestRuleAppending:
    """Tests for rule appending functionality."""

    def test_append_rules_adds_to_list(self) -> None:
        """Test that append_rules adds rules to the list."""
        manager = ContextManager()

        manager.append_rules(["Rule 1", "Rule 2"])

        assert "Rule 1" in manager._custom_rules
        assert "Rule 2" in manager._custom_rules

    def test_append_rules_maintains_order(self) -> None:
        """Test that rules maintain insertion order."""
        manager = ContextManager()

        manager.append_rules(["First"])
        manager.append_rules(["Second"])
        manager.append_rules(["Third"])

        assert manager._custom_rules == ["First", "Second", "Third"]

    def test_appended_rules_included_in_context(self, tmp_path: Path) -> None:
        """Test that appended rules are included in generated context."""
        manager = ContextManager()

        manager.append_rules(["Global rule 1", "Global rule 2"])
        manager.update_context("pm", {"mission": "Test"})

        path = manager.generate_claude_md(tmp_path)
        content = path.read_text()

        assert "Global rule 1" in content
        assert "Global rule 2" in content

    def test_append_rules_updates_current_context(self) -> None:
        """Test that appending rules updates current context."""
        manager = ContextManager()
        manager.update_context("pm", {"mission": "Test"})

        initial_count = len(manager._current_context.rules)  # type: ignore

        manager.append_rules(["New rule"])

        assert len(manager._current_context.rules) == initial_count + 1  # type: ignore


class TestClearContext:
    """Tests for clearing context."""

    def test_clear_resets_context(self) -> None:
        """Test that clear_context resets the context."""
        manager = ContextManager()
        manager.update_context("pm", {"mission": "Test"})
        manager.append_rules(["Custom rule"])

        manager.clear_context()

        assert manager._current_context is None
        assert manager._custom_rules == []
        assert manager._version == 0


class TestContextInfo:
    """Tests for context information retrieval."""

    def test_get_context_info_no_context(self) -> None:
        """Test get_context_info when no context is set."""
        manager = ContextManager()

        info = manager.get_context_info()

        assert info["has_context"] is False
        assert info["version"] == 0

    def test_get_context_info_with_context(self) -> None:
        """Test get_context_info when context is set."""
        manager = ContextManager()
        manager.update_context(
            "pm",
            {
                "mission": "Test",
                "guidelines": ["G1", "G2"],
                "artifacts": ["A1"],
            },
        )

        info = manager.get_context_info()

        assert info["has_context"] is True
        assert info["phase"] == "pm"
        assert info["mission_set"] is True
        assert info["guideline_count"] == 2
        assert info["artifact_count"] == 1
        assert info["version"] == 1


class TestPhaseTemplates:
    """Tests for phase template retrieval."""

    def test_get_phase_template_valid(self) -> None:
        """Test getting template for valid phase."""
        manager = ContextManager()

        template = manager.get_phase_template("pm")

        assert "role" in template
        assert "focus" in template
        assert "default_guidelines" in template

    def test_get_phase_template_invalid(self) -> None:
        """Test getting template for invalid phase."""
        manager = ContextManager()

        template = manager.get_phase_template("invalid")

        assert template == {}

    def test_all_phases_have_templates(self) -> None:
        """Test that all phases have templates defined."""
        manager = ContextManager()

        for phase in ["pm", "arch", "eng", "qa"]:
            template = manager.get_phase_template(phase)
            assert "role" in template
            assert "default_guidelines" in template


class TestGenerateSampleContexts:
    """Tests for sample context generation."""

    def test_generate_samples_creates_files(self, tmp_path: Path) -> None:
        """Test that sample generation creates files for all phases."""
        paths = generate_sample_contexts(tmp_path)

        assert len(paths) == 4

        for path in paths:
            assert path.exists()
            assert path.name == "CLAUDE.md"

    def test_generate_samples_valid_content(self, tmp_path: Path) -> None:
        """Test that generated samples have valid content."""
        paths = generate_sample_contexts(tmp_path)

        for path in paths:
            content = path.read_text()
            assert "# Project Context" in content
            assert "Current Phase" in content
            assert "TaskFlow" in content  # Sample project name


class TestAtomicWrites:
    """Tests for atomic file write operations."""

    def test_no_partial_writes_on_success(self, tmp_path: Path) -> None:
        """Test that successful writes are complete."""
        manager = ContextManager()
        manager.update_context("pm", {"mission": "Complete content"})

        path = manager.generate_claude_md(tmp_path)
        content = path.read_text()

        # Verify complete content
        assert "# Project Context" in content
        assert "Complete content" in content

    def test_no_temp_file_remains(self, tmp_path: Path) -> None:
        """Test that temporary file is removed after write."""
        manager = ContextManager()
        manager.update_context("pm", {"mission": "Test"})

        manager.generate_claude_md(tmp_path)

        # Check no temp file
        temp_files = list(tmp_path.glob(".CLAUDE.md.tmp"))
        assert len(temp_files) == 0
