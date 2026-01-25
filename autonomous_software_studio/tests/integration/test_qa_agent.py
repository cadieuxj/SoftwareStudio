"""Integration tests for QA Agent.

Tests cover:
- Test generation from acceptance criteria
- Successful test execution (all pass)
- Failed test execution (bug report generation)
- Bug report format validation
- Severity classification
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.wrappers.claude_wrapper import ExecutionResult
from src.wrappers.qa_agent import (
    BugReportValidationError,
    QAAgent,
    TestResult,
    TestSummary,
)
from src.wrappers.state import create_initial_state


# Sample PRD with acceptance criteria
SAMPLE_PRD = """
# Product Requirements Document

## 1. User Stories

As a user, I want to log in securely.
As a user, I want to manage my tasks.

## 2. Functional Requirements

FR-001: User authentication
FR-002: Task creation

## 3. Non-Functional Requirements

- Response time under 200ms

## 4. Acceptance Criteria

- Given valid credentials, when user logs in, then show dashboard
- Given invalid credentials, when user logs in, then show error message
- Given a logged-in user, when they create a task, then it appears in their list
- Given an empty task title, when user tries to create task, then show validation error
"""


class TestQAAgentAcceptanceCriteria:
    """Tests for acceptance criteria extraction."""

    def test_extract_criteria_from_prd(self, tmp_path: Path) -> None:
        """Test successful extraction of acceptance criteria."""
        prd_path = tmp_path / "docs" / "PRD.md"
        prd_path.parent.mkdir(parents=True)
        prd_path.write_text(SAMPLE_PRD)

        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path)

        agent = QAAgent()
        criteria = agent._extract_acceptance_criteria(state)

        assert len(criteria) > 0
        # Should contain Given/When/Then criteria
        criteria_text = " ".join(criteria)
        assert "valid credentials" in criteria_text.lower()

    def test_extract_criteria_no_prd(self, tmp_path: Path) -> None:
        """Test extraction returns empty list when no PRD."""
        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        )
        # No PRD path

        agent = QAAgent()
        criteria = agent._extract_acceptance_criteria(state)

        assert criteria == []

    def test_extract_criteria_prd_without_section(self, tmp_path: Path) -> None:
        """Test extraction when PRD lacks acceptance criteria section."""
        prd_content = """
# PRD

## User Stories
Some stories

## Requirements
Some requirements
"""
        prd_path = tmp_path / "PRD.md"
        prd_path.write_text(prd_content)

        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path)

        agent = QAAgent()
        criteria = agent._extract_acceptance_criteria(state)

        assert criteria == []


class TestQAAgentTestGeneration:
    """Tests for test case generation."""

    def test_generate_tests_creates_file(self, tmp_path: Path) -> None:
        """Test that test file is generated from criteria."""
        prd_path = tmp_path / "PRD.md"
        prd_path.write_text(SAMPLE_PRD)

        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path)

        agent = QAAgent()
        criteria = agent._extract_acceptance_criteria(state)
        test_file = agent._generate_tests(state, criteria)

        assert test_file is not None
        assert test_file.exists()
        assert "test_" in test_file.name

        content = test_file.read_text()
        assert "import pytest" in content
        assert "class TestAcceptanceCriteria" in content

    def test_generate_tests_no_criteria(self, tmp_path: Path) -> None:
        """Test that no file is generated when no criteria."""
        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        )

        agent = QAAgent()
        test_file = agent._generate_tests(state, [])

        assert test_file is None

    def test_criterion_to_test_name(self) -> None:
        """Test conversion of criterion to test name."""
        agent = QAAgent()

        criterion = "Given valid credentials, when user logs in, then show dashboard"
        name = agent._criterion_to_test_name(criterion, 1)

        assert name.startswith("test_")
        assert name.endswith("_1")
        # Should contain key words
        assert any(word in name for word in ["given", "valid", "credentials"])


class TestQAAgentExecution:
    """Tests for QA Agent execution."""

    @patch("src.wrappers.qa_agent.QAAgent._execute_claude")
    def test_execute_all_tests_pass(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test execution when all tests pass."""
        # Setup
        prd_path = tmp_path / "docs" / "PRD.md"
        prd_path.parent.mkdir(parents=True)
        prd_path.write_text(SAMPLE_PRD)

        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()

        mock_execute.return_value = ExecutionResult(
            success=True,
            stdout="""
Running tests...
TEST_RESULTS_START
{
  "total": 5,
  "passed": 5,
  "failed": 0,
  "errors": 0,
  "failures": []
}
TEST_RESULTS_END
All tests passed!
""",
            stderr="",
            exit_code=0,
            execution_time=10.0,
        )

        agent = QAAgent()
        state = create_initial_state(
            mission="Test implementation",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path, current_phase="qa")

        with patch.object(agent, "get_system_prompt", return_value="Test prompt"):
            new_state = agent.execute(state)

        assert new_state.qa_passed is True
        assert new_state.path_bug_report is None
        assert new_state.current_phase == "complete"

    @patch("src.wrappers.qa_agent.QAAgent._execute_claude")
    def test_execute_tests_fail(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test execution when tests fail generates bug report."""
        prd_path = tmp_path / "docs" / "PRD.md"
        prd_path.parent.mkdir(parents=True)
        prd_path.write_text(SAMPLE_PRD)

        mock_execute.return_value = ExecutionResult(
            success=True,
            stdout="""
Running tests...
TEST_RESULTS_START
{
  "total": 5,
  "passed": 3,
  "failed": 2,
  "errors": 0,
  "failures": [
    {
      "test": "test_login_valid_credentials",
      "criterion": "Given valid credentials, when user logs in, then show dashboard",
      "error": "AssertionError: Expected 200, got 500",
      "trace": "File test.py, line 10..."
    }
  ]
}
TEST_RESULTS_END
""",
            stderr="",
            exit_code=0,
            execution_time=15.0,
        )

        agent = QAAgent()
        state = create_initial_state(
            mission="Test implementation",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path, current_phase="qa")

        with patch.object(agent, "get_system_prompt", return_value="prompt"):
            new_state = agent.execute(state)

        assert new_state.qa_passed is False
        assert new_state.path_bug_report is not None
        assert new_state.path_bug_report.exists()

        # Check bug report content
        report_content = new_state.path_bug_report.read_text()
        assert "Bug Report" in report_content
        assert "Test Execution Summary" in report_content

    def test_state_immutability_preserved(self, tmp_path: Path) -> None:
        """Test that original state is not modified."""
        prd_path = tmp_path / "PRD.md"
        prd_path.write_text(SAMPLE_PRD)

        original_state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path, current_phase="qa")

        agent = QAAgent()

        with patch.object(agent, "_execute_claude") as mock_exec:
            mock_exec.return_value = ExecutionResult(
                success=True,
                stdout="5 passed",
                stderr="",
                exit_code=0,
            )
            with patch.object(agent, "get_system_prompt", return_value="prompt"):
                new_state = agent.execute(original_state)

        # Original unchanged
        assert original_state.qa_passed is None
        assert original_state.path_bug_report is None


class TestQAAgentConfiguration:
    """Tests for QA Agent configuration."""

    def test_default_timeout(self) -> None:
        """Test default timeout is 300 seconds (5 minutes)."""
        agent = QAAgent()
        assert agent._timeout == 300

    def test_profile_name(self) -> None:
        """Test profile name is 'qa'."""
        agent = QAAgent()
        assert agent.profile_name == "qa"

    def test_role_description(self) -> None:
        """Test role description mentions QA/testing."""
        agent = QAAgent()
        assert "QA" in agent.role_description

    def test_severity_levels_defined(self) -> None:
        """Test severity levels are defined."""
        assert "Critical" in QAAgent.SEVERITY_LEVELS
        assert "High" in QAAgent.SEVERITY_LEVELS
        assert "Medium" in QAAgent.SEVERITY_LEVELS
        assert "Low" in QAAgent.SEVERITY_LEVELS


class TestBugReportGeneration:
    """Tests for bug report generation."""

    def test_generate_bug_report(self, tmp_path: Path) -> None:
        """Test bug report generation with failures."""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()

        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
            project_name="TestProject",
        )

        summary = TestSummary(
            total=5,
            passed=3,
            failed=2,
            errors=0,
            results=[
                TestResult(
                    name="test_login_failure",
                    passed=False,
                    error_message="AssertionError: Expected 200",
                    criterion="Given valid credentials...",
                    stack_trace="File test.py, line 10",
                ),
            ],
        )

        criteria = [
            "Given valid credentials, when user logs in, then show dashboard",
            "Given invalid credentials, when user logs in, then show error",
        ]

        agent = QAAgent()
        report_path = agent._generate_bug_report(
            state, summary, criteria, reports_dir
        )

        assert report_path.exists()
        content = report_path.read_text()

        # Check structure
        assert "# QA Bug Report" in content
        assert "Test Execution Summary" in content
        assert "Total Tests**: 5" in content
        assert "Passed**: 3" in content
        assert "Failed**: 2" in content
        assert "Failed Test Details" in content
        assert "Acceptance Criteria Coverage" in content

    def test_classify_severity_critical(self) -> None:
        """Test severity classification for critical bugs."""
        agent = QAAgent()

        result = TestResult(
            name="test_security",
            passed=False,
            error_message="Security vulnerability in authentication",
        )

        severity = agent._classify_severity(result)
        assert severity == "Critical"

    def test_classify_severity_high(self) -> None:
        """Test severity classification for high bugs."""
        agent = QAAgent()

        result = TestResult(
            name="test_error",
            passed=False,
            error_message="Exception: Database connection failed",
        )

        severity = agent._classify_severity(result)
        assert severity == "High"

    def test_classify_severity_medium(self) -> None:
        """Test severity classification for medium bugs."""
        agent = QAAgent()

        result = TestResult(
            name="test_assertion",
            passed=False,
            error_message="assert 5 == 4 is False",
        )

        severity = agent._classify_severity(result)
        assert severity == "Medium"


class TestTestResultParsing:
    """Tests for test result parsing."""

    def test_parse_structured_results(self, tmp_path: Path) -> None:
        """Test parsing structured JSON results from output."""
        output = """
TEST_RESULTS_START
{
  "total": 10,
  "passed": 8,
  "failed": 2,
  "errors": 0,
  "failures": [
    {
      "test": "test_example",
      "error": "Failed assertion"
    }
  ]
}
TEST_RESULTS_END
"""
        state = create_initial_state(mission="Test", work_dir=tmp_path)
        agent = QAAgent()

        summary = agent._parse_test_results(state, output)

        assert summary.total == 10
        assert summary.passed == 8
        assert summary.failed == 2
        assert len(summary.results) == 1

    def test_parse_pytest_output(self) -> None:
        """Test parsing pytest console output."""
        output = """
======================== test session starts ========================
collected 5 items

test_example.py::test_one PASSED
test_example.py::test_two PASSED
test_example.py::test_three FAILED

======================== 2 passed, 1 failed in 1.23s ========================
"""
        agent = QAAgent()
        summary = agent._parse_pytest_output(output)

        assert summary.passed == 2
        assert summary.failed == 1

    def test_parse_all_passed(self) -> None:
        """Test parsing output when all tests pass."""
        output = """
======================== test session starts ========================
collected 10 items

test_example.py .......... [100%]

======================== 10 passed in 2.34s ========================
"""
        agent = QAAgent()
        summary = agent._parse_pytest_output(output)

        assert summary.passed == 10
        assert summary.failed == 0


class TestValidation:
    """Tests for artifact validation."""

    def test_validate_bug_report_valid(self, tmp_path: Path) -> None:
        """Test validation passes for valid bug report."""
        report_content = """
# QA Bug Report

## Test Execution Summary

- Total Tests: 5
- Passed: 3
- Failed: 2

## Failed Tests

Details here...
"""
        report_path = tmp_path / "BUG_REPORT.md"
        report_path.write_text(report_content)

        agent = QAAgent()
        result = agent.validate_output(report_path)

        assert result is True

    def test_validate_bug_report_missing_summary(self, tmp_path: Path) -> None:
        """Test validation fails when summary is missing."""
        report_content = """
# QA Bug Report

## Failed Tests
Some failures here
"""
        report_path = tmp_path / "BUG_REPORT.md"
        report_path.write_text(report_content)

        agent = QAAgent()
        result = agent._validate_bug_report(report_path)

        assert result is False

    def test_validate_test_file_valid(self, tmp_path: Path) -> None:
        """Test validation passes for valid Python test file."""
        test_content = """
import pytest

def test_example():
    assert True
"""
        test_path = tmp_path / "test_example.py"
        test_path.write_text(test_content)

        agent = QAAgent()
        result = agent.validate_output(test_path)

        assert result is True

    def test_validate_test_file_syntax_error(self, tmp_path: Path) -> None:
        """Test validation fails for test file with syntax error."""
        test_content = """
def test_broken(
    assert True
"""
        test_path = tmp_path / "test_broken.py"
        test_path.write_text(test_content)

        agent = QAAgent()
        result = agent.validate_output(test_path)

        assert result is False

    def test_validate_nonexistent_file(self, tmp_path: Path) -> None:
        """Test validation fails for non-existent file."""
        agent = QAAgent()
        result = agent.validate_output(tmp_path / "nonexistent.md")

        assert result is False


class TestQAIntegrationScenarios:
    """Integration scenarios for QA Agent."""

    @patch("src.wrappers.qa_agent.QAAgent._execute_claude")
    def test_full_qa_cycle_with_failures(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test complete QA cycle with test failures."""
        # Setup PRD
        prd_path = tmp_path / "docs" / "PRD.md"
        prd_path.parent.mkdir(parents=True)
        prd_path.write_text(SAMPLE_PRD)

        mock_execute.return_value = ExecutionResult(
            success=True,
            stdout="""
TEST_RESULTS_START
{
  "total": 4,
  "passed": 2,
  "failed": 2,
  "errors": 0,
  "failures": [
    {
      "test": "test_login_valid",
      "criterion": "Given valid credentials...",
      "error": "HTTP 500 instead of 200",
      "trace": "Stack trace here"
    },
    {
      "test": "test_task_create",
      "criterion": "Given a logged-in user...",
      "error": "Task not created",
      "trace": "Another trace"
    }
  ]
}
TEST_RESULTS_END
""",
            stderr="",
            exit_code=0,
            execution_time=20.0,
        )

        agent = QAAgent()
        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path, current_phase="qa")

        with patch.object(agent, "get_system_prompt", return_value="prompt"):
            new_state = agent.execute(state)

        # Verify results
        assert new_state.qa_passed is False
        assert new_state.path_bug_report is not None

        # Check bug report
        report = new_state.path_bug_report.read_text()
        assert "test_login_valid" in report or "login" in report.lower()
        assert "2" in report  # Failed count

        # Check execution recorded
        assert len(new_state.execution_history) == 1

    @patch("src.wrappers.qa_agent.QAAgent._execute_claude")
    def test_qa_completes_pipeline_on_success(
        self, mock_execute: MagicMock, tmp_path: Path
    ) -> None:
        """Test that successful QA marks pipeline as complete."""
        prd_path = tmp_path / "PRD.md"
        prd_path.write_text(SAMPLE_PRD)

        mock_execute.return_value = ExecutionResult(
            success=True,
            stdout="10 passed in 5.0s",
            stderr="",
            exit_code=0,
        )

        agent = QAAgent()
        state = create_initial_state(
            mission="Test",
            work_dir=tmp_path,
        ).with_update(path_prd=prd_path, current_phase="qa")

        with patch.object(agent, "get_system_prompt", return_value="prompt"):
            new_state = agent.execute(state)

        assert new_state.qa_passed is True
        assert new_state.current_phase == "complete"
