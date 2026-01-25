"""Integration tests for PM Agent.

Tests cover:
- PRD generation from sample mission
- PRD validation passes for valid document
- PRD validation fails for incomplete document
- State update includes correct path
- Timeout handling for long missions
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.wrappers.claude_wrapper import ExecutionResult
from src.wrappers.pm_agent import PMAgent, PRDValidationError
from src.wrappers.state import create_initial_state


class TestPMAgentValidation:
    """Tests for PRD validation logic."""

    def test_validate_output_valid_prd(self, tmp_path: Path) -> None:
        """Test validation passes for a valid PRD."""
        prd_content = """
# Product Requirements Document

## Executive Summary

This document outlines the comprehensive requirements for a task management application
designed for teams and individuals to track their work effectively. The application
will provide a robust set of features for task creation, organization, and tracking.
The target users include project managers, team leads, and individual contributors
who need to manage their daily work activities efficiently.

## 1. User Stories

As a team member, I want to create tasks with detailed descriptions so that I can
clearly communicate what needs to be done to my colleagues.

As a project manager, I want to assign tasks to team members so that I can distribute
work effectively across my team.

As a user, I want to mark tasks as complete so that I can track my progress and
know what work remains to be done.

As a user, I want to set due dates on tasks so that I can prioritize my work
based on deadlines and manage my time effectively.

As a user, I want to categorize tasks into projects so that I can organize my work
and easily find related tasks.

As a user, I want to search tasks by keyword so that I can quickly find specific
items without browsing through all my tasks.

## 2. Functional Requirements

FR-001: The system shall allow users to create new tasks with a title (required),
description (optional), due date (optional), and priority level (optional).

FR-002: The system shall allow users to edit all properties of existing tasks
including title, description, due date, priority, and status.

FR-003: The system shall allow users to delete tasks with a confirmation prompt
to prevent accidental deletion of important items.

FR-004: The system shall allow users to mark tasks as complete or incomplete
with a single click or tap action.

FR-005: The system shall allow users to set priority levels (High, Medium, Low)
for tasks to help with work prioritization.

FR-006: The system shall allow users to filter tasks by status, priority, due date,
and project/category for efficient task management.

FR-007: The system shall allow users to search tasks using full-text search
across task titles and descriptions.

## 3. Non-Functional Requirements

### Performance Requirements
- Page load time shall be under 2 seconds for 95% of requests
- API response time shall be under 200ms for read operations
- The application shall support 10,000 concurrent users minimum

### Security Requirements
- All data shall be encrypted in transit using TLS 1.2 or higher
- User authentication shall be required for all operations
- Password requirements: minimum 8 characters with mixed case and numbers

### Scalability Requirements
- The system shall support horizontal scaling to handle increased load
- Database shall be designed to support 1 million tasks per user

### Reliability Requirements
- System uptime shall be 99.9% excluding scheduled maintenance windows
- Data backup shall be performed daily with 30-day retention

## 4. Acceptance Criteria

Given a logged-in user, when they click "New Task", then a task creation form
appears with fields for title, description, due date, and priority.

Given a task creation form, when the user enters valid data and submits, then
a new task is created and appears in their task list immediately.

Given an existing task, when the user clicks the "Complete" button, then the
task status is updated to complete and visual feedback is provided.

Given a task list, when the user enters a search term in the search box, then
only tasks matching the search term are displayed in the results.

Given invalid input data, when the user tries to create or edit a task, then
appropriate error messages are displayed to guide the user.

## Assumptions

- Users have stable internet connectivity for application use
- Users have modern web browsers (Chrome, Firefox, Safari, Edge)
- Users have basic familiarity with task management concepts

## Out of Scope

- Mobile native applications (future phase)
- Offline mode functionality (future phase)
- Third-party calendar integrations (future phase)
- Email notifications (future phase)
"""
        prd_path = tmp_path / "PRD.md"
        prd_path.write_text(prd_content)

        agent = PMAgent()
        result = agent.validate_output(prd_path)

        assert result is True

    def test_validate_output_missing_user_stories(self, tmp_path: Path) -> None:
        """Test validation fails when User Stories section is missing."""
        prd_content = """
# Product Requirements Document

## Functional Requirements
- Feature 1
- Feature 2

## Non-Functional Requirements
- Performance target

## Acceptance Criteria
Given context, when action, then result.
"""
        prd_path = tmp_path / "PRD.md"
        prd_path.write_text(prd_content)

        agent = PMAgent()

        with pytest.raises(PRDValidationError) as exc_info:
            agent.validate_output(prd_path)

        assert "User Stories" in str(exc_info.value)

    def test_validate_output_missing_functional_requirements(
        self, tmp_path: Path
    ) -> None:
        """Test validation fails when Functional Requirements missing."""
        prd_content = """
# Product Requirements Document

## User Stories
As a user, I want to do things so that I can achieve goals.
As a user, I want feature 2 so that benefit 2.
As a user, I want feature 3 so that benefit 3.
As a user, I want feature 4 so that benefit 4.
As a user, I want feature 5 so that benefit 5.

## Non-Functional Requirements
- Performance requirements here

## Acceptance Criteria
Given context, when action, then result.
"""
        prd_path = tmp_path / "PRD.md"
        prd_path.write_text(prd_content)

        agent = PMAgent()

        with pytest.raises(PRDValidationError) as exc_info:
            agent.validate_output(prd_path)

        assert "Functional Requirements" in str(exc_info.value)

    def test_validate_output_missing_acceptance_criteria(self, tmp_path: Path) -> None:
        """Test validation fails when Acceptance Criteria missing."""
        prd_content = """
# Product Requirements Document

## User Stories
As a user, I want to do things.

## Functional Requirements
- Feature 1

## Non-Functional Requirements
- Performance requirements
"""
        prd_path = tmp_path / "PRD.md"
        prd_path.write_text(prd_content)

        agent = PMAgent()

        with pytest.raises(PRDValidationError) as exc_info:
            agent.validate_output(prd_path)

        assert "Acceptance Criteria" in str(exc_info.value)

    def test_validate_output_insufficient_word_count(self, tmp_path: Path) -> None:
        """Test validation fails when word count is below minimum."""
        prd_content = """
# PRD

## User Stories
Story 1

## Functional Requirements
Requirement 1

## Non-Functional Requirements
NFR 1

## Acceptance Criteria
Criteria 1
"""
        prd_path = tmp_path / "PRD.md"
        prd_path.write_text(prd_content)

        agent = PMAgent()

        with pytest.raises(PRDValidationError) as exc_info:
            agent.validate_output(prd_path)

        assert "words" in str(exc_info.value).lower()
        assert "500" in str(exc_info.value)

    def test_validate_output_nonexistent_file(self, tmp_path: Path) -> None:
        """Test validation fails for non-existent file."""
        nonexistent = tmp_path / "nonexistent.md"

        agent = PMAgent()

        with pytest.raises(PRDValidationError) as exc_info:
            agent.validate_output(nonexistent)

        assert "not found" in str(exc_info.value).lower()


class TestPMAgentExecution:
    """Tests for PM Agent execution."""

    @patch("src.wrappers.pm_agent.PMAgent._execute_claude")
    def test_execute_success(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful PRD generation."""
        # Create a valid PRD that will be "generated" (500+ words)
        valid_prd = """
# Product Requirements Document

## Executive Summary

This document outlines the comprehensive requirements for a task management application
designed for teams and individuals to track their work effectively. The application
will provide a robust set of features for task creation, organization, and tracking.
The target users include project managers, team leads, and individual contributors
who need to manage their daily work activities efficiently.

## 1. User Stories

As a team member, I want to create tasks with detailed descriptions so that I can
clearly communicate what needs to be done to my colleagues.

As a project manager, I want to assign tasks to team members so that I can distribute
work effectively across my team and ensure all work is properly allocated.

As a user, I want to mark tasks as complete so that I can track my progress and
know what work remains to be done throughout the project lifecycle.

As a user, I want to set due dates on tasks so that I can prioritize my work
based on deadlines and manage my time effectively.

As a user, I want to categorize tasks into projects so that I can organize my work
and easily find related tasks when needed.

## 2. Functional Requirements

FR-001: The system shall allow users to create new tasks with a title (required),
description (optional), due date (optional), and priority level (optional).

FR-002: The system shall allow users to edit all properties of existing tasks
including title, description, due date, priority, and status.

FR-003: The system shall allow users to delete tasks with a confirmation prompt
to prevent accidental deletion of important items.

FR-004: The system shall allow users to mark tasks as complete or incomplete
with a single click action and visual feedback.

FR-005: The system shall allow users to set priority levels (High, Medium, Low)
for tasks to help with work prioritization and planning.

FR-006: The system shall allow users to filter tasks by status, priority, due date,
and project/category for efficient task management.

## 3. Non-Functional Requirements

### Performance Requirements
- Page load time shall be under 2 seconds for 95% of requests
- API response time shall be under 200ms for read operations
- The application shall support 10,000 concurrent users minimum

### Security Requirements
- All data shall be encrypted in transit using TLS 1.2 or higher
- User authentication shall be required for all operations
- Passwords stored with bcrypt hashing algorithm

### Scalability Requirements
- The system shall support horizontal scaling to handle increased load
- Database shall be designed to support 1 million tasks per user

## 4. Acceptance Criteria

Given a logged-in user, when they click "New Task", then a task creation form
appears with fields for title, description, due date, and priority.

Given a task creation form, when the user enters valid data and submits, then
a new task is created and appears in their task list immediately.

Given an existing task, when the user clicks the "Complete" button, then the
task status is updated to complete and visual feedback is provided.

Given a task list, when the user enters a search term in the search box, then
only tasks matching the search term are displayed in the results.

## Assumptions

- Users have stable internet connectivity for application use
- Users have modern web browsers (Chrome, Firefox, Safari, Edge)

## Out of Scope

- Mobile native applications (future phase)
- Offline mode functionality (future phase)
- Third-party calendar integrations (future phase)
"""
        # Set up mock
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        prd_path = docs_dir / "PRD.md"

        def create_prd(*args, **kwargs):
            prd_path.write_text(valid_prd)
            return ExecutionResult(
                success=True,
                stdout="PRD generated successfully",
                stderr="",
                exit_code=0,
                artifacts_created=[prd_path],
                execution_time=5.0,
            )

        mock_execute.side_effect = create_prd

        # Create agent and execute
        agent = PMAgent()
        state = create_initial_state(
            mission="Build a task management application",
            work_dir=tmp_path,
        )

        # Mock the system prompt loading
        with patch.object(agent, "get_system_prompt", return_value="Test prompt"):
            new_state = agent.execute(state)

        # Verify
        assert new_state.path_prd == prd_path
        assert new_state.current_phase == "arch"
        assert len(new_state.errors) == 0
        assert prd_path in new_state.files_created

    @patch("src.wrappers.pm_agent.PMAgent._execute_claude")
    def test_execute_failure(self, mock_execute: MagicMock, tmp_path: Path) -> None:
        """Test handling of execution failure."""
        mock_execute.return_value = ExecutionResult(
            success=False,
            stdout="",
            stderr="Execution failed: timeout",
            exit_code=1,
            execution_time=180.0,
        )

        agent = PMAgent()
        state = create_initial_state(
            mission="Build something",
            work_dir=tmp_path,
        )

        with patch.object(agent, "get_system_prompt", return_value="Test prompt"):
            new_state = agent.execute(state)

        assert new_state.current_phase == "failed"
        assert len(new_state.errors) > 0
        assert "failed" in new_state.errors[0].lower()

    @patch("src.wrappers.pm_agent.PMAgent._execute_claude")
    def test_execute_prd_not_created(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test handling when PRD file is not created."""
        mock_execute.return_value = ExecutionResult(
            success=True,
            stdout="Completed but no file created",
            stderr="",
            exit_code=0,
            artifacts_created=[],
            execution_time=5.0,
        )

        agent = PMAgent()
        state = create_initial_state(
            mission="Build something",
            work_dir=tmp_path,
        )

        with patch.object(agent, "get_system_prompt", return_value="Test prompt"):
            new_state = agent.execute(state)

        assert new_state.current_phase == "failed"
        assert len(new_state.errors) > 0

    def test_state_immutability_preserved(self, tmp_path: Path) -> None:
        """Test that original state is not modified."""
        original_state = create_initial_state(
            mission="Build a task app",
            work_dir=tmp_path,
        )

        agent = PMAgent()

        # Even if execution fails, original state should be unchanged
        with patch.object(agent, "_execute_claude") as mock_exec:
            mock_exec.return_value = ExecutionResult(
                success=False,
                stdout="",
                stderr="Error",
                exit_code=1,
            )
            with patch.object(agent, "get_system_prompt", return_value="prompt"):
                new_state = agent.execute(original_state)

        # Original state unchanged
        assert original_state.current_phase == "pm"
        assert original_state.path_prd is None
        assert len(original_state.errors) == 0

        # New state has changes
        assert new_state is not original_state


class TestPMAgentConfiguration:
    """Tests for PM Agent configuration."""

    def test_default_timeout(self) -> None:
        """Test that PM agent has 180 second timeout by default."""
        agent = PMAgent()
        assert agent._timeout == 180

    def test_profile_name(self) -> None:
        """Test PM agent profile name."""
        agent = PMAgent()
        assert agent.profile_name == "pm"

    def test_role_description(self) -> None:
        """Test PM agent role description."""
        agent = PMAgent()
        assert "Product Manager" in agent.role_description

    def test_required_sections(self) -> None:
        """Test that required sections are properly defined."""
        assert "User Stories" in PMAgent.REQUIRED_SECTIONS
        assert "Functional Requirements" in PMAgent.REQUIRED_SECTIONS
        assert "Non-Functional Requirements" in PMAgent.REQUIRED_SECTIONS
        assert "Acceptance Criteria" in PMAgent.REQUIRED_SECTIONS

    def test_min_word_count(self) -> None:
        """Test minimum word count requirement."""
        assert PMAgent.MIN_WORD_COUNT == 500


class TestPRDExtraction:
    """Tests for PRD content extraction from output."""

    def test_extract_prd_markdown_block(self) -> None:
        """Test extraction from markdown code block."""
        output = """
Some preamble text...

```markdown
# Product Requirements Document

## User Stories
As a user, I want things.

## Functional Requirements
- Feature 1

## Non-Functional Requirements
- Performance

## Acceptance Criteria
Given x, when y, then z.
```

Some trailing text...
"""
        agent = PMAgent()
        content = agent._extract_prd_from_output(output)

        assert content is not None
        assert "Product Requirements Document" in content

    def test_extract_prd_no_content(self) -> None:
        """Test extraction returns None when no PRD found."""
        output = "Just some random output without a PRD"

        agent = PMAgent()
        content = agent._extract_prd_from_output(output)

        assert content is None

    def test_extract_prd_too_short(self) -> None:
        """Test extraction returns None for very short content."""
        output = """
```markdown
# PRD
Short
```
"""
        agent = PMAgent()
        content = agent._extract_prd_from_output(output)

        assert content is None  # Less than 200 chars


class TestPMAgentIntegrationScenarios:
    """Integration test scenarios for PM Agent."""

    @patch("src.wrappers.pm_agent.PMAgent._execute_claude")
    def test_state_update_includes_metrics(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test that execution metrics are recorded in state."""
        valid_prd = """
# Product Requirements Document

## Executive Summary

This document outlines the comprehensive requirements for a task management application
designed for teams and individuals to track their work effectively. The application
will provide a robust set of features for task creation, organization, and tracking.
The target users include project managers, team leads, and individual contributors
who need to manage their daily work activities efficiently.

## 1. User Stories

As a team member, I want to create tasks with detailed descriptions so that I can
clearly communicate what needs to be done to my colleagues.

As a project manager, I want to assign tasks to team members so that I can distribute
work effectively across my team and ensure all work is properly allocated.

As a user, I want to mark tasks as complete so that I can track my progress and
know what work remains to be done throughout the project lifecycle.

As a user, I want to set due dates on tasks so that I can prioritize my work
based on deadlines and manage my time effectively.

As a user, I want to categorize tasks into projects so that I can organize my work
and easily find related tasks when needed.

## 2. Functional Requirements

FR-001: The system shall allow users to create new tasks with a title (required),
description (optional), due date (optional), and priority level (optional).

FR-002: The system shall allow users to edit all properties of existing tasks
including title, description, due date, priority, and status.

FR-003: The system shall allow users to delete tasks with a confirmation prompt
to prevent accidental deletion of important items.

FR-004: The system shall allow users to mark tasks as complete or incomplete
with a single click action and visual feedback.

FR-005: The system shall allow users to set priority levels (High, Medium, Low)
for tasks to help with work prioritization and planning.

FR-006: The system shall allow users to filter tasks by status, priority, due date,
and project/category for efficient task management.

## 3. Non-Functional Requirements

### Performance Requirements
- Page load time shall be under 2 seconds for 95% of requests
- API response time shall be under 200ms for read operations
- The application shall support 10,000 concurrent users minimum

### Security Requirements
- All data shall be encrypted in transit using TLS 1.2 or higher
- User authentication shall be required for all operations
- Passwords stored with bcrypt hashing algorithm

### Scalability Requirements
- The system shall support horizontal scaling to handle increased load
- Database shall be designed to support 1 million tasks per user

## 4. Acceptance Criteria

Given a logged-in user, when they click "New Task", then a task creation form
appears with fields for title, description, due date, and priority.

Given a task creation form, when the user enters valid data and submits, then
a new task is created and appears in their task list immediately.

Given an existing task, when the user clicks the "Complete" button, then the
task status is updated to complete and visual feedback is provided.

Given a task list, when the user enters a search term in the search box, then
only tasks matching the search term are displayed in the results.

## Assumptions

- Users have stable internet connectivity for application use
- Users have modern web browsers (Chrome, Firefox, Safari, Edge)

## Out of Scope

- Mobile native applications (future phase)
- Offline mode functionality (future phase)
- Third-party calendar integrations (future phase)
"""

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        prd_path = docs_dir / "PRD.md"

        def create_prd(*args, **kwargs):
            prd_path.write_text(valid_prd)
            return ExecutionResult(
                success=True,
                stdout="Generated PRD" + "x" * 1000,  # Long output for metrics
                stderr="",
                exit_code=0,
                artifacts_created=[prd_path],
                execution_time=10.5,
            )

        mock_execute.side_effect = create_prd

        agent = PMAgent()
        state = create_initial_state(mission="Test", work_dir=tmp_path)

        with patch.object(agent, "get_system_prompt", return_value="prompt"):
            new_state = agent.execute(state)

        # Check metrics were recorded
        assert len(new_state.execution_history) == 1
        metrics = new_state.execution_history[0]["metrics"]
        assert metrics["execution_time_seconds"] == 10.5
        assert metrics["tokens_output"] > 0
