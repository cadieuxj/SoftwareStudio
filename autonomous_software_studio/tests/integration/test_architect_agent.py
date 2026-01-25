"""Integration tests for Architect Agent.

Tests cover:
- TECH_SPEC generation from PRD
- scaffold.sh generation and execution
- Directory structure creation
- Validation of incomplete specs
- Rules of Engagement parsing
"""

from __future__ import annotations

import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.wrappers.architect_agent import (
    ArchitectAgent,
    ScaffoldValidationError,
    TechSpecValidationError,
)
from src.wrappers.claude_wrapper import ExecutionResult
from src.wrappers.state import create_initial_state


# Sample valid PRD for testing
SAMPLE_PRD = """
# Product Requirements Document

## 1. User Stories

As a user, I want to create tasks so that I can track my work.
As a user, I want to mark tasks complete so that I know what's done.
As a user, I want to set due dates so that I can prioritize work.
As a user, I want to categorize tasks so that I can organize work.
As a user, I want to search tasks so that I can find items quickly.

## 2. Functional Requirements

FR-001: Users can create new tasks with title and description.
FR-002: Users can edit existing tasks.
FR-003: Users can delete tasks.
FR-004: Users can mark tasks as complete.
FR-005: Users can set priority levels.

## 3. Non-Functional Requirements

- Response time under 200ms
- Support 1000 concurrent users
- 99.9% uptime

## 4. Acceptance Criteria

Given a user is logged in, when they create a task, then it appears in their list.
Given a task exists, when the user marks it complete, then status updates.
"""

# Sample valid Tech Spec
SAMPLE_TECH_SPEC = """
# Technical Specification

## 1. Architecture Overview

This system uses a layered architecture with clear separation of concerns.

```mermaid
graph TB
    API[REST API] --> SVC[Services]
    SVC --> REPO[Repository]
    REPO --> DB[(Database)]
```

### Technology Stack
- Python 3.10+
- FastAPI for web framework
- SQLAlchemy for ORM
- PostgreSQL for database

## 2. Directory Structure

```
project/
├── src/
│   ├── models/
│   ├── api/
│   ├── services/
│   └── repositories/
├── tests/
└── docs/
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

```yaml
paths:
  /api/tasks:
    get:
      summary: List all tasks
    post:
      summary: Create a task
```

## 5. Third-Party Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.109.0 | Web framework |
| pydantic | >=2.0.0 | Validation |
| sqlalchemy | >=2.0.0 | ORM |

## 6. Rules of Engagement

### Coding Standards
- Use type hints for all functions
- Docstrings in Google format
- Use Pytest for testing
- Maintain 80% code coverage
- No global variables

### Testing Requirements
- Unit tests for all business logic
- Integration tests for API endpoints
"""

# Sample scaffold script
SAMPLE_SCAFFOLD = """#!/bin/bash
set -e

echo "Creating project structure..."

mkdir -p src/models
mkdir -p src/api
mkdir -p src/services
mkdir -p src/repositories
mkdir -p tests/unit
mkdir -p tests/integration

touch src/__init__.py
touch src/models/__init__.py
touch src/api/__init__.py

echo "Done!"
"""


class TestArchitectAgentValidation:
    """Tests for Tech Spec and Scaffold validation logic."""

    def test_validate_output_valid_spec(self, tmp_path: Path) -> None:
        """Test validation passes for a valid tech spec."""
        spec_path = tmp_path / "TECH_SPEC.md"
        spec_path.write_text(SAMPLE_TECH_SPEC)

        agent = ArchitectAgent()
        result = agent.validate_output(spec_path)

        assert result is True

    def test_validate_output_missing_architecture_overview(
        self, tmp_path: Path
    ) -> None:
        """Test validation fails when Architecture Overview is missing."""
        spec_content = """
# Technical Specification

## Directory Structure
Some structure

## Data Models
Some models

## API Signatures
Some APIs

## Third-Party Dependencies
Some deps

## Rules of Engagement
Some rules
"""
        spec_path = tmp_path / "TECH_SPEC.md"
        spec_path.write_text(spec_content)

        agent = ArchitectAgent()

        with pytest.raises(TechSpecValidationError) as exc_info:
            agent.validate_output(spec_path)

        assert "Architecture Overview" in str(exc_info.value)

    def test_validate_output_missing_directory_structure(
        self, tmp_path: Path
    ) -> None:
        """Test validation fails when Directory Structure is missing."""
        spec_content = """
# Technical Specification

## Architecture Overview
Some architecture

## Data Models
Some models

## API Signatures
Some APIs

## Third-Party Dependencies
Some deps

## Rules of Engagement
Some rules
"""
        spec_path = tmp_path / "TECH_SPEC.md"
        spec_path.write_text(spec_content)

        agent = ArchitectAgent()

        with pytest.raises(TechSpecValidationError) as exc_info:
            agent.validate_output(spec_path)

        assert "Directory Structure" in str(exc_info.value)

    def test_validate_output_missing_data_models(self, tmp_path: Path) -> None:
        """Test validation fails when Data Models section is missing."""
        spec_content = """
# Technical Specification

## Architecture Overview
Some architecture

## Directory Structure
Some structure

## API Signatures
Some APIs

## Third-Party Dependencies
Some deps

## Rules of Engagement
Some rules
"""
        spec_path = tmp_path / "TECH_SPEC.md"
        spec_path.write_text(spec_content)

        agent = ArchitectAgent()

        with pytest.raises(TechSpecValidationError) as exc_info:
            agent.validate_output(spec_path)

        assert "Data Models" in str(exc_info.value)

    def test_validate_output_nonexistent_file(self, tmp_path: Path) -> None:
        """Test validation fails for non-existent file."""
        nonexistent = tmp_path / "nonexistent.md"

        agent = ArchitectAgent()

        with pytest.raises(TechSpecValidationError) as exc_info:
            agent.validate_output(nonexistent)

        assert "not found" in str(exc_info.value).lower()

    def test_validate_scaffold_valid(self, tmp_path: Path) -> None:
        """Test scaffold validation passes for valid script."""
        scaffold_path = tmp_path / "scaffold.sh"
        scaffold_path.write_text(SAMPLE_SCAFFOLD)
        scaffold_path.chmod(0o755)

        agent = ArchitectAgent()
        result = agent._validate_scaffold(scaffold_path)

        assert result is True

    def test_validate_scaffold_missing_shebang(self, tmp_path: Path) -> None:
        """Test scaffold validation fails without shebang."""
        scaffold_content = """
echo "No shebang!"
mkdir -p src
"""
        scaffold_path = tmp_path / "scaffold.sh"
        scaffold_path.write_text(scaffold_content)

        agent = ArchitectAgent()

        with pytest.raises(ScaffoldValidationError) as exc_info:
            agent._validate_scaffold(scaffold_path)

        assert "shebang" in str(exc_info.value).lower()

    def test_validate_scaffold_no_mkdir(self, tmp_path: Path) -> None:
        """Test scaffold validation fails without mkdir commands."""
        scaffold_content = """#!/bin/bash
echo "No directories created"
touch file.txt
"""
        scaffold_path = tmp_path / "scaffold.sh"
        scaffold_path.write_text(scaffold_content)

        agent = ArchitectAgent()

        with pytest.raises(ScaffoldValidationError) as exc_info:
            agent._validate_scaffold(scaffold_path)

        assert "directories" in str(exc_info.value).lower()

    def test_validate_scaffold_makes_executable(self, tmp_path: Path) -> None:
        """Test that scaffold validation makes script executable."""
        scaffold_path = tmp_path / "scaffold.sh"
        scaffold_path.write_text(SAMPLE_SCAFFOLD)
        scaffold_path.chmod(0o644)  # Not executable initially

        agent = ArchitectAgent()
        agent._validate_scaffold(scaffold_path)

        # Check it's now executable
        mode = scaffold_path.stat().st_mode
        assert mode & stat.S_IXUSR


class TestArchitectAgentExecution:
    """Tests for Architect Agent execution."""

    @patch("src.wrappers.architect_agent.ArchitectAgent._execute_claude")
    def test_execute_success(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful tech spec and scaffold generation."""
        # Setup directories
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create PRD
        prd_path = docs_dir / "PRD.md"
        prd_path.write_text(SAMPLE_PRD)

        spec_path = docs_dir / "TECH_SPEC.md"
        scaffold_path = docs_dir / "scaffold.sh"

        def create_artifacts(*args, **kwargs):
            spec_path.write_text(SAMPLE_TECH_SPEC)
            scaffold_path.write_text(SAMPLE_SCAFFOLD)
            scaffold_path.chmod(0o755)
            return ExecutionResult(
                success=True,
                stdout="Generated tech spec and scaffold",
                stderr="",
                exit_code=0,
                artifacts_created=[spec_path, scaffold_path],
                execution_time=15.0,
            )

        mock_execute.side_effect = create_artifacts

        agent = ArchitectAgent()
        state = create_initial_state(
            mission="Build task management app",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path, current_phase="arch")

        with patch.object(agent, "get_system_prompt", return_value="Test prompt"):
            new_state = agent.execute(state)

        assert new_state.path_tech_spec == spec_path
        assert new_state.path_scaffold_script == scaffold_path
        assert new_state.current_phase == "eng"
        assert len(new_state.errors) == 0

    @patch("src.wrappers.architect_agent.ArchitectAgent._execute_claude")
    def test_execute_missing_prd(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test execution fails when PRD is missing."""
        agent = ArchitectAgent()
        state = create_initial_state(
            mission="Build something",
            work_dir=tmp_path,
        ).with_update(current_phase="arch")
        # No PRD path set

        new_state = agent.execute(state)

        assert new_state.current_phase == "failed"
        assert len(new_state.errors) > 0
        assert "prd" in new_state.errors[0].lower()
        mock_execute.assert_not_called()

    @patch("src.wrappers.architect_agent.ArchitectAgent._execute_claude")
    def test_execute_failure(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test handling of execution failure."""
        # Create PRD
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        prd_path = docs_dir / "PRD.md"
        prd_path.write_text(SAMPLE_PRD)

        mock_execute.return_value = ExecutionResult(
            success=False,
            stdout="",
            stderr="Execution failed",
            exit_code=1,
            execution_time=10.0,
        )

        agent = ArchitectAgent()
        state = create_initial_state(
            mission="Build something",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path, current_phase="arch")

        with patch.object(agent, "get_system_prompt", return_value="prompt"):
            new_state = agent.execute(state)

        assert new_state.current_phase == "failed"
        assert len(new_state.errors) > 0

    def test_state_immutability_preserved(self, tmp_path: Path) -> None:
        """Test that original state is not modified."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        prd_path = docs_dir / "PRD.md"
        prd_path.write_text(SAMPLE_PRD)

        original_state = create_initial_state(
            mission="Build task app",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path, current_phase="arch")

        agent = ArchitectAgent()

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
        assert original_state.current_phase == "arch"
        assert original_state.path_tech_spec is None
        assert len(original_state.errors) == 0


class TestArchitectAgentConfiguration:
    """Tests for Architect Agent configuration."""

    def test_default_timeout(self) -> None:
        """Test default timeout is 300 seconds (5 minutes)."""
        agent = ArchitectAgent()
        assert agent._timeout == 300

    def test_profile_name(self) -> None:
        """Test profile name is 'arch'."""
        agent = ArchitectAgent()
        assert agent.profile_name == "arch"

    def test_role_description(self) -> None:
        """Test role description mentions architect."""
        agent = ArchitectAgent()
        assert "Architect" in agent.role_description

    def test_required_sections(self) -> None:
        """Test that all required sections are defined."""
        assert "Architecture Overview" in ArchitectAgent.REQUIRED_SPEC_SECTIONS
        assert "Directory Structure" in ArchitectAgent.REQUIRED_SPEC_SECTIONS
        assert "Data Models" in ArchitectAgent.REQUIRED_SPEC_SECTIONS
        assert "API Signatures" in ArchitectAgent.REQUIRED_SPEC_SECTIONS
        assert "Third-Party Dependencies" in ArchitectAgent.REQUIRED_SPEC_SECTIONS
        assert "Rules of Engagement" in ArchitectAgent.REQUIRED_SPEC_SECTIONS


class TestSpecExtraction:
    """Tests for tech spec extraction from output."""

    def test_extract_spec_markdown_block(self) -> None:
        """Test extraction from markdown code block."""
        output = """
Some preamble text about what was generated...

```markdown
# Technical Specification

## Architecture Overview
This system uses a layered architecture with clear separation of concerns.
The architecture consists of a presentation layer, business logic layer,
and data access layer. We use FastAPI for the web framework and SQLAlchemy
for the ORM. PostgreSQL is used for the database.

## Directory Structure
The project follows a standard Python package layout with src/ containing
all source code, tests/ containing test files, and docs/ containing documentation.

## Data Models
Pydantic models are used for validation and SQLAlchemy for persistence.
Each entity has both a schema for validation and a model for database operations.

## API Signatures
RESTful API endpoints following OpenAPI specification. All endpoints
require authentication and return JSON responses with proper error handling.

## Third-Party Dependencies
FastAPI, Pydantic, SQLAlchemy, Alembic, Pytest for the core stack.

## Rules of Engagement
All code must have type hints and docstrings. Unit test coverage must be at least 80%.
```

Trailing text about the generation process...
"""
        agent = ArchitectAgent()
        content = agent._extract_spec_from_output(output)

        assert content is not None
        assert "Technical Specification" in content

    def test_extract_spec_no_content(self) -> None:
        """Test extraction returns None when no spec found."""
        output = "Just some random output"

        agent = ArchitectAgent()
        content = agent._extract_spec_from_output(output)

        assert content is None

    def test_extract_scaffold_bash_block(self) -> None:
        """Test extraction of scaffold from bash code block."""
        output = """
Here's the scaffold:

```bash
#!/bin/bash
mkdir -p src/models
mkdir -p src/api
touch src/__init__.py
echo "Done"
```

End of output.
"""
        agent = ArchitectAgent()
        content = agent._extract_scaffold_from_output(output)

        assert content is not None
        assert "#!/bin/bash" in content
        assert "mkdir" in content

    def test_extract_scaffold_no_content(self) -> None:
        """Test extraction returns None when no scaffold found."""
        output = "No scaffold script here"

        agent = ArchitectAgent()
        content = agent._extract_scaffold_from_output(output)

        assert content is None


class TestArchitectIntegrationScenarios:
    """Integration scenarios for Architect Agent."""

    @patch("src.wrappers.architect_agent.ArchitectAgent._execute_claude")
    def test_state_includes_both_artifacts(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test that both tech spec and scaffold are tracked in state."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        prd_path = docs_dir / "PRD.md"
        prd_path.write_text(SAMPLE_PRD)

        spec_path = docs_dir / "TECH_SPEC.md"
        scaffold_path = docs_dir / "scaffold.sh"

        def create_artifacts(*args, **kwargs):
            spec_path.write_text(SAMPLE_TECH_SPEC)
            scaffold_path.write_text(SAMPLE_SCAFFOLD)
            scaffold_path.chmod(0o755)
            return ExecutionResult(
                success=True,
                stdout="Done",
                stderr="",
                exit_code=0,
                artifacts_created=[spec_path, scaffold_path],
                execution_time=20.0,
            )

        mock_execute.side_effect = create_artifacts

        agent = ArchitectAgent()
        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path, current_phase="arch")

        with patch.object(agent, "get_system_prompt", return_value="prompt"):
            new_state = agent.execute(state)

        assert spec_path in new_state.files_created
        assert scaffold_path in new_state.files_created
        assert len(new_state.execution_history) == 1

    @patch("src.wrappers.architect_agent.ArchitectAgent._execute_claude")
    def test_continues_without_scaffold(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test that execution continues even if scaffold isn't created."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        prd_path = docs_dir / "PRD.md"
        prd_path.write_text(SAMPLE_PRD)

        spec_path = docs_dir / "TECH_SPEC.md"

        def create_spec_only(*args, **kwargs):
            spec_path.write_text(SAMPLE_TECH_SPEC)
            return ExecutionResult(
                success=True,
                stdout="Done",
                stderr="",
                exit_code=0,
                artifacts_created=[spec_path],
                execution_time=15.0,
            )

        mock_execute.side_effect = create_spec_only

        agent = ArchitectAgent()
        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path, current_phase="arch")

        with patch.object(agent, "get_system_prompt", return_value="prompt"):
            new_state = agent.execute(state)

        # Should succeed even without scaffold
        assert new_state.current_phase == "eng"
        assert new_state.path_tech_spec == spec_path
        assert new_state.path_scaffold_script is None
