"""Integration tests for Engineer Agent.

Tests cover:
- Batch execution for each layer
- Code quality validation
- Import validation
- Rejection of feature additions
- Error handling implementation
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.wrappers.claude_wrapper import ExecutionResult
from src.wrappers.engineer_agent import (
    BatchExecutionError,
    CodeValidationError,
    EngineerAgent,
    ImplementationBatch,
)
from src.wrappers.state import create_initial_state


# Sample Tech Spec for testing
SAMPLE_TECH_SPEC = """
# Technical Specification

## 1. Architecture Overview

Layered architecture with API, Service, and Repository layers.

```mermaid
graph TB
    API --> SVC[Services]
    SVC --> REPO[Repository]
    REPO --> DB[(Database)]
```

## 2. Directory Structure

```
project/
├── src/
│   ├── models/
│   ├── api/
│   ├── services/
│   └── repositories/
└── tests/
```

## 3. Data Models

```python
from pydantic import BaseModel

class TaskCreate(BaseModel):
    title: str
    description: str

class Task(TaskCreate):
    id: int
    completed: bool = False
```

## 4. API Signatures

- GET /api/tasks - List all tasks
- POST /api/tasks - Create a task
- PUT /api/tasks/{id} - Update a task
- DELETE /api/tasks/{id} - Delete a task

## 5. Third-Party Dependencies

| Library | Version |
|---------|---------|
| fastapi | >=0.109.0 |
| pydantic | >=2.0.0 |

## 6. Rules of Engagement

### Coding Standards
- Use type hints for all functions
- Docstrings in Google format
- Use Pytest for testing
- Maintain 80% code coverage
- No global variables
- No magic numbers

### Testing Requirements
- Unit tests for all business logic
- Integration tests for API endpoints
"""


class TestEngineerAgentCodeValidation:
    """Tests for code quality validation."""

    def test_validate_output_valid_code(self, tmp_path: Path) -> None:
        """Test validation passes for valid Python code."""
        code_content = '''
"""Valid module with proper implementation."""

from typing import List


def process_items(items: List[str]) -> int:
    """Process a list of items.

    Args:
        items: List of items to process.

    Returns:
        Count of processed items.
    """
    processed = 0
    for item in items:
        if item:
            processed += 1
    return processed
'''
        code_path = tmp_path / "valid.py"
        code_path.write_text(code_content)

        agent = EngineerAgent()
        result = agent.validate_output(code_path)

        assert result is True

    def test_validate_output_with_todo(self, tmp_path: Path) -> None:
        """Test validation fails when code contains TODO."""
        code_content = '''
def process() -> None:
    # TODO: implement this later
    pass
'''
        code_path = tmp_path / "with_todo.py"
        code_path.write_text(code_content)

        agent = EngineerAgent()
        result = agent.validate_output(code_path)

        assert result is False

    def test_validate_output_with_fixme(self, tmp_path: Path) -> None:
        """Test validation fails when code contains FIXME."""
        code_content = '''
def process() -> None:
    # FIXME: this is broken
    return None
'''
        code_path = tmp_path / "with_fixme.py"
        code_path.write_text(code_content)

        agent = EngineerAgent()
        result = agent.validate_output(code_path)

        assert result is False

    def test_validate_output_with_not_implemented(self, tmp_path: Path) -> None:
        """Test validation fails when code raises NotImplementedError."""
        code_content = '''
def process() -> None:
    raise NotImplementedError
'''
        code_path = tmp_path / "not_implemented.py"
        code_path.write_text(code_content)

        agent = EngineerAgent()
        result = agent.validate_output(code_path)

        assert result is False

    def test_validate_output_syntax_error(self, tmp_path: Path) -> None:
        """Test validation fails for invalid Python syntax."""
        code_content = '''
def broken(
    return "missing closing paren"
'''
        code_path = tmp_path / "syntax_error.py"
        code_path.write_text(code_content)

        agent = EngineerAgent()
        result = agent.validate_output(code_path)

        assert result is False

    def test_validate_output_nonexistent_file(self, tmp_path: Path) -> None:
        """Test validation fails for non-existent file."""
        nonexistent = tmp_path / "nonexistent.py"

        agent = EngineerAgent()
        result = agent.validate_output(nonexistent)

        assert result is False

    def test_validate_output_non_python(self, tmp_path: Path) -> None:
        """Test validation passes for non-Python files."""
        md_path = tmp_path / "readme.md"
        md_path.write_text("# README\nSome content")

        agent = EngineerAgent()
        result = agent.validate_output(md_path)

        assert result is True


class TestEngineerAgentExecution:
    """Tests for Engineer Agent execution."""

    @patch("src.wrappers.engineer_agent.EngineerAgent._execute_claude")
    def test_execute_success(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful code implementation."""
        # Setup
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        spec_path = docs_dir / "TECH_SPEC.md"
        spec_path.write_text(SAMPLE_TECH_SPEC)

        # Create source directories
        src_dir = tmp_path / "src"
        (src_dir / "models").mkdir(parents=True)
        (src_dir / "api").mkdir(parents=True)
        (src_dir / "services").mkdir(parents=True)

        def create_code(*args, **kwargs):
            # Create some valid Python files
            model_file = src_dir / "models" / "entities.py"
            model_file.write_text('''
"""Entity models."""

from pydantic import BaseModel

class Task(BaseModel):
    """Task model."""
    id: int
    title: str
    completed: bool = False
''')
            return ExecutionResult(
                success=True,
                stdout="Implementation complete",
                stderr="",
                exit_code=0,
                artifacts_created=[model_file],
                execution_time=30.0,
            )

        mock_execute.side_effect = create_code

        agent = EngineerAgent()
        state = create_initial_state(
            mission="Implement task management",
            work_dir=tmp_path,
        ).with_update(path_tech_spec=spec_path, current_phase="eng")

        with patch.object(agent, "get_system_prompt", return_value="Test prompt"):
            new_state = agent.execute(state)

        assert new_state.current_phase == "qa"
        assert len(new_state.errors) == 0
        assert len(new_state.files_created) > 0

    @patch("src.wrappers.engineer_agent.EngineerAgent._execute_claude")
    def test_execute_missing_tech_spec(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test execution fails when tech spec is missing."""
        agent = EngineerAgent()
        state = create_initial_state(
            mission="Implement something",
            work_dir=tmp_path,
        ).with_update(current_phase="eng")
        # No tech spec set

        new_state = agent.execute(state)

        assert new_state.current_phase == "failed"
        assert len(new_state.errors) > 0
        assert "tech_spec" in new_state.errors[0].lower()
        mock_execute.assert_not_called()

    @patch("src.wrappers.engineer_agent.EngineerAgent._execute_claude")
    def test_execute_batch_failure(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test handling when a batch execution fails."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        spec_path = docs_dir / "TECH_SPEC.md"
        spec_path.write_text(SAMPLE_TECH_SPEC)

        mock_execute.return_value = ExecutionResult(
            success=False,
            stdout="",
            stderr="Batch failed",
            exit_code=1,
        )

        agent = EngineerAgent()
        state = create_initial_state(
            mission="Implement",
            work_dir=tmp_path,
        ).with_update(path_tech_spec=spec_path, current_phase="eng")

        with patch.object(agent, "get_system_prompt", return_value="prompt"):
            new_state = agent.execute(state)

        assert new_state.current_phase == "failed"
        assert len(new_state.errors) > 0

    def test_state_immutability_preserved(self, tmp_path: Path) -> None:
        """Test that original state is not modified."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        spec_path = docs_dir / "TECH_SPEC.md"
        spec_path.write_text(SAMPLE_TECH_SPEC)

        original_state = create_initial_state(
            mission="Implement",
            work_dir=tmp_path,
        ).with_update(path_tech_spec=spec_path, current_phase="eng")

        agent = EngineerAgent()

        with patch.object(agent, "_execute_claude") as mock_exec:
            mock_exec.return_value = ExecutionResult(
                success=False,
                stdout="",
                stderr="Error",
                exit_code=1,
            )
            with patch.object(agent, "get_system_prompt", return_value="prompt"):
                new_state = agent.execute(original_state)

        # Original unchanged
        assert original_state.current_phase == "eng"
        assert len(original_state.files_created) == 0


class TestEngineerAgentConfiguration:
    """Tests for Engineer Agent configuration."""

    def test_default_timeout(self) -> None:
        """Test default timeout is 600 seconds (10 minutes)."""
        agent = EngineerAgent()
        assert agent._timeout == 600

    def test_profile_name(self) -> None:
        """Test profile name is 'eng'."""
        agent = EngineerAgent()
        assert agent.profile_name == "eng"

    def test_role_description(self) -> None:
        """Test role description mentions engineer/developer."""
        agent = EngineerAgent()
        assert "Developer" in agent.role_description or "Engineer" in agent.role_description

    def test_implementation_batches_defined(self) -> None:
        """Test that all implementation batches are defined."""
        batch_names = [b.name for b in EngineerAgent.IMPLEMENTATION_BATCHES]
        assert "models" in batch_names
        assert "api" in batch_names
        assert "services" in batch_names

    def test_forbidden_patterns_defined(self) -> None:
        """Test that forbidden patterns are defined."""
        assert len(EngineerAgent.FORBIDDEN_PATTERNS) > 0
        # Should include common placeholder patterns
        patterns_str = " ".join(EngineerAgent.FORBIDDEN_PATTERNS)
        assert "TODO" in patterns_str
        assert "FIXME" in patterns_str
        assert "NotImplementedError" in patterns_str


class TestRulesExtraction:
    """Tests for Rules of Engagement extraction."""

    def test_extract_rules_success(self, tmp_path: Path) -> None:
        """Test successful extraction of rules from tech spec."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        spec_path = docs_dir / "TECH_SPEC.md"
        spec_path.write_text(SAMPLE_TECH_SPEC)

        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        ).with_update(path_tech_spec=spec_path)

        agent = EngineerAgent()
        rules = agent._extract_rules(state)

        assert len(rules) > 0
        # Should contain rules from the spec
        rules_text = " ".join(rules)
        assert "type hints" in rules_text.lower() or "docstring" in rules_text.lower()

    def test_extract_rules_no_spec(self, tmp_path: Path) -> None:
        """Test extraction returns empty when no spec."""
        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        )
        # No tech spec

        agent = EngineerAgent()
        rules = agent._extract_rules(state)

        assert rules == []


class TestClaudeMdUpdate:
    """Tests for CLAUDE.md update functionality."""

    def test_update_claude_md(self, tmp_path: Path) -> None:
        """Test that CLAUDE.md is created with proper content."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        spec_path = docs_dir / "TECH_SPEC.md"
        spec_path.write_text(SAMPLE_TECH_SPEC)

        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        ).with_update(path_tech_spec=spec_path)

        agent = EngineerAgent()
        rules = ["Use type hints", "Write tests"]
        agent._update_claude_md(state, rules)

        claude_md = tmp_path / "CLAUDE.md"
        assert claude_md.exists()

        content = claude_md.read_text()
        assert "Technical Specification" in content
        assert "Rules of Engagement" in content
        assert "Use type hints" in content


class TestImplementationBatches:
    """Tests for implementation batch logic."""

    def test_batches_have_correct_order(self) -> None:
        """Test that batches are ordered correctly."""
        batches = sorted(
            EngineerAgent.IMPLEMENTATION_BATCHES, key=lambda b: b.order
        )

        # Models should come first (database layer)
        assert batches[0].name == "models"
        # API should come second
        assert batches[1].name == "api"

    def test_batches_have_directories(self) -> None:
        """Test that all batches have target directories."""
        for batch in EngineerAgent.IMPLEMENTATION_BATCHES:
            assert len(batch.directories) > 0
            assert batch.scope  # Has scope description


class TestCodeValidationIntegration:
    """Integration tests for code validation."""

    def test_validate_implementation_multiple_issues(self, tmp_path: Path) -> None:
        """Test validation catches multiple code issues."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create more than 5 files with issues to trigger the exception
        (src_dir / "file1.py").write_text("# TODO: implement")
        (src_dir / "file2.py").write_text("# FIXME: broken")
        (src_dir / "file3.py").write_text("# TODO: another todo")
        (src_dir / "file4.py").write_text("# XXX: needs work")
        (src_dir / "file5.py").write_text("# TODO: more todos")
        (src_dir / "file6.py").write_text("# FIXME: also broken")
        # Valid file
        (src_dir / "file7.py").write_text("def valid(): pass")

        files = [
            src_dir / "file1.py",
            src_dir / "file2.py",
            src_dir / "file3.py",
            src_dir / "file4.py",
            src_dir / "file5.py",
            src_dir / "file6.py",
            src_dir / "file7.py",
        ]

        agent = EngineerAgent()

        # Should raise because of more than 5 issues
        with pytest.raises(CodeValidationError):
            agent._validate_implementation(tmp_path, files)

    def test_validate_implementation_passes_clean_code(
        self, tmp_path: Path
    ) -> None:
        """Test validation passes for clean code."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create clean files
        (src_dir / "clean1.py").write_text('"""Clean module."""\ndef func(): pass')
        (src_dir / "clean2.py").write_text('"""Another clean module."""\nx = 1')

        files = [
            src_dir / "clean1.py",
            src_dir / "clean2.py",
        ]

        agent = EngineerAgent()

        # Should not raise
        agent._validate_implementation(tmp_path, files)


class TestEngineerIntegrationScenarios:
    """Integration scenarios for Engineer Agent."""

    @patch("src.wrappers.engineer_agent.EngineerAgent._execute_claude")
    def test_metrics_aggregated_across_batches(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test that execution metrics are aggregated across batches."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        spec_path = docs_dir / "TECH_SPEC.md"
        spec_path.write_text(SAMPLE_TECH_SPEC)

        # Create directories
        src_dir = tmp_path / "src"
        for subdir in ["models", "api", "services"]:
            (src_dir / subdir).mkdir(parents=True)

        call_count = 0

        def create_code(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return ExecutionResult(
                success=True,
                stdout=f"Batch {call_count} complete",
                stderr="",
                exit_code=0,
                artifacts_created=[],
                execution_time=10.0,  # 10 seconds per batch
            )

        mock_execute.side_effect = create_code

        agent = EngineerAgent()
        state = create_initial_state(
            mission="Implement",
            work_dir=tmp_path,
        ).with_update(path_tech_spec=spec_path, current_phase="eng")

        with patch.object(agent, "get_system_prompt", return_value="prompt"):
            new_state = agent.execute(state)

        # Should have executed multiple batches
        assert call_count >= 3

        # Should have execution recorded
        assert len(new_state.execution_history) == 1
        metrics = new_state.execution_history[0]["metrics"]
        # Execution time should be aggregated
        assert metrics["execution_time_seconds"] >= 30.0  # At least 3 batches
