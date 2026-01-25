"""QA Engineer Agent for testing and validation.

The QA Agent is the fourth and final stage of the Four-Persona Waterfall pipeline.
It tests the implementation against acceptance criteria and generates bug reports.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
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


class TestExecutionError(AgentError):
    """Raised when test execution fails."""

    pass


class BugReportValidationError(ArtifactValidationError):
    """Raised when bug report validation fails."""

    pass


@dataclass
class TestResult:
    """Result of a test execution.

    Attributes:
        name: Test name.
        passed: Whether the test passed.
        error_message: Error message if failed.
        criterion: Related acceptance criterion.
        stack_trace: Full stack trace if available.
    """

    name: str
    passed: bool
    error_message: str | None = None
    criterion: str | None = None
    stack_trace: str | None = None


@dataclass
class TestSummary:
    """Summary of all test results.

    Attributes:
        total: Total number of tests.
        passed: Number of passed tests.
        failed: Number of failed tests.
        errors: Number of tests with errors.
        results: Individual test results.
    """

    total: int
    passed: int
    failed: int
    errors: int
    results: list[TestResult]


class QAAgent(BaseAgent):
    """QA Engineer Agent for testing and bug reporting.

    This agent is responsible for:
    - Loading PRD acceptance criteria
    - Generating pytest test cases
    - Executing tests via bash
    - Parsing test results (JSON format)
    - Generating detailed bug reports if failures

    The QA agent has read-only access to source code and generates
    actionable bug reports that link failures to acceptance criteria.

    Attributes:
        REPORTS_DIR: Directory for reports.
        BUG_REPORT_FILE: Filename for bug reports.
        TEST_RESULTS_FILE: Filename for JSON test results.
        SEVERITY_LEVELS: Bug severity classification.
    """

    REPORTS_DIR: ClassVar[str] = "reports"
    BUG_REPORT_FILE: ClassVar[str] = "BUG_REPORT.md"
    TEST_RESULTS_FILE: ClassVar[str] = "test_results.json"
    SEVERITY_LEVELS: ClassVar[list[str]] = ["Critical", "High", "Medium", "Low"]

    def __init__(
        self,
        env_manager: "EnvironmentManager | None" = None,
        timeout: int | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize QA Agent with appropriate timeout."""
        super().__init__(
            env_manager=env_manager,
            timeout=timeout or 300,  # 5 minutes for testing
            log_dir=log_dir,
        )

    @property
    def profile_name(self) -> str:
        """Return the QA profile name."""
        return "qa"

    @property
    def role_description(self) -> str:
        """Return the QA role description."""
        return (
            "Adversarial QA Engineer specialized in finding bugs and breaking software. "
            "Tests implementation against acceptance criteria."
        )

    def execute(self, state: AgentState) -> AgentState:
        """Execute the QA agent to test the implementation.

        Args:
            state: The current pipeline state.

        Returns:
            Updated state with qa_passed flag and optional bug report path.

        Raises:
            AgentError: If QA execution fails.
        """
        self._logger.info("Starting QA agent execution")

        # Ensure reports directory exists
        reports_dir = state.work_dir / self.REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Extract acceptance criteria from PRD
        criteria = self._extract_acceptance_criteria(state)
        self._logger.info(f"Found {len(criteria)} acceptance criteria")

        # Generate test cases
        test_file = self._generate_tests(state, criteria)
        if test_file:
            self._logger.info(f"Generated test file: {test_file}")

        # Execute tests
        system_prompt = self.get_system_prompt(state)
        execution_prompt = self._build_execution_prompt(state, criteria, system_prompt)

        result = self._execute_claude(
            prompt=execution_prompt,
            work_dir=state.work_dir,
        )

        # Parse test results
        test_summary = self._parse_test_results(state, result.stdout)
        self._logger.info(
            f"Test results: {test_summary.passed}/{test_summary.total} passed"
        )

        # Calculate metrics
        metrics = self._calculate_metrics(result)

        # Determine if QA passed
        qa_passed = test_summary.failed == 0 and test_summary.errors == 0

        # Generate bug report if failures
        bug_report_path: Path | None = None
        if not qa_passed:
            bug_report_path = self._generate_bug_report(
                state, test_summary, criteria, reports_dir
            )
            self._logger.info(f"Bug report generated: {bug_report_path}")

        # Update state
        files_created: list[Path] = []
        if test_file and test_file.exists():
            files_created.append(test_file)
        if bug_report_path:
            files_created.append(bug_report_path)

        new_state = (
            state.with_update(
                qa_passed=qa_passed,
                path_bug_report=bug_report_path,
            )
            .add_files(files_created)
            .add_execution(metrics, self.profile_name)
        )

        # Transition to complete or back to eng for fixes
        if qa_passed:
            new_state = new_state.mark_complete()
            self._logger.info("QA passed! Pipeline complete.")
        else:
            # Stay in QA phase so orchestrator can decide next steps
            self._logger.info(
                f"QA failed with {test_summary.failed} failures. "
                "Bug report generated."
            )

        return new_state

    def _extract_acceptance_criteria(self, state: AgentState) -> list[str]:
        """Extract acceptance criteria from PRD.

        Args:
            state: Current state with PRD path.

        Returns:
            List of acceptance criteria strings.
        """
        if not state.path_prd or not state.path_prd.exists():
            self._logger.warning("PRD not found, no acceptance criteria available")
            return []

        content = state.path_prd.read_text(encoding="utf-8")

        # Find acceptance criteria section
        patterns = [
            r"##\s*(?:\d+\.\s*)?Acceptance Criteria\s*\n(.*?)(?=\n##|\Z)",
            r"###\s*Acceptance Criteria\s*\n(.*?)(?=\n###|\n##|\Z)",
        ]

        criteria: list[str] = []
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                section = match.group(1)
                # Extract individual criteria (Given/When/Then or bullet points)
                for line in section.split("\n"):
                    line = line.strip()
                    if line.startswith("-") or line.startswith("*"):
                        criteria.append(line.lstrip("-* ").strip())
                    elif re.match(r"^\d+\.", line):
                        criteria.append(re.sub(r"^\d+\.\s*", "", line).strip())
                    elif line.lower().startswith("given"):
                        criteria.append(line)
                break

        return [c for c in criteria if c]  # Filter empty

    def _generate_tests(
        self,
        state: AgentState,
        criteria: list[str],
    ) -> Path | None:
        """Generate pytest test cases from acceptance criteria.

        Args:
            state: Current state.
            criteria: List of acceptance criteria.

        Returns:
            Path to generated test file, or None if generation failed.
        """
        if not criteria:
            return None

        tests_dir = state.work_dir / "tests" / "acceptance"
        tests_dir.mkdir(parents=True, exist_ok=True)

        test_file = tests_dir / "test_acceptance_criteria.py"

        # Generate test cases
        test_content = self._generate_test_content(criteria)
        test_file.write_text(test_content, encoding="utf-8")

        return test_file

    def _generate_test_content(self, criteria: list[str]) -> str:
        """Generate test file content from criteria.

        Args:
            criteria: List of acceptance criteria.

        Returns:
            Python test file content.
        """
        lines = [
            '"""Acceptance criteria tests.',
            "",
            "Auto-generated by QA Agent from PRD acceptance criteria.",
            '"""',
            "",
            "import pytest",
            "",
            "",
            "class TestAcceptanceCriteria:",
            '    """Tests mapped from PRD acceptance criteria."""',
            "",
        ]

        for i, criterion in enumerate(criteria, 1):
            # Create test name from criterion
            test_name = self._criterion_to_test_name(criterion, i)
            lines.extend([
                f"    def {test_name}(self) -> None:",
                f'        """Test: {criterion[:80]}..."""',
                f"        # Criterion: {criterion}",
                "        # TODO: Implement test logic",
                "        pytest.skip('Test not yet implemented')",
                "",
            ])

        return "\n".join(lines)

    def _criterion_to_test_name(self, criterion: str, index: int) -> str:
        """Convert acceptance criterion to test function name.

        Args:
            criterion: The acceptance criterion text.
            index: Index for uniqueness.

        Returns:
            Valid Python function name.
        """
        # Extract key words
        words = re.findall(r"\w+", criterion.lower())[:5]
        name = "_".join(words) if words else f"criterion_{index}"
        return f"test_{name}_{index}"

    def _build_execution_prompt(
        self,
        state: AgentState,
        criteria: list[str],
        system_prompt: str,
    ) -> str:
        """Build execution prompt for QA testing.

        Args:
            state: Current state.
            criteria: Acceptance criteria.
            system_prompt: Base system prompt.

        Returns:
            Complete execution prompt.
        """
        criteria_text = "\n".join(f"- {c}" for c in criteria)

        prompt = f"""
{system_prompt}

---

## Acceptance Criteria from PRD

{criteria_text}

---

## Instructions

Your goal is to thoroughly test the implementation against the acceptance criteria.

1. Review the implementation in src/
2. For each acceptance criterion, create appropriate tests:
   - Happy path (positive) tests
   - Edge case tests
   - Error handling (negative) tests
3. Execute tests using: pytest tests/ --json-report --json-report-file=reports/test_results.json -v
4. Analyze any failures
5. If failures exist, identify:
   - Which acceptance criterion failed
   - Root cause analysis
   - Specific file and line causing the issue
   - Recommended fix

Generate comprehensive tests and execute them. Be adversarial - your goal is to find bugs!

After running tests, output the results in this format:
TEST_RESULTS_START
{{
  "total": <number>,
  "passed": <number>,
  "failed": <number>,
  "errors": <number>,
  "failures": [
    {{
      "test": "<test_name>",
      "criterion": "<related_criterion>",
      "error": "<error_message>",
      "trace": "<stack_trace>"
    }}
  ]
}}
TEST_RESULTS_END
"""
        return prompt.strip()

    def _parse_test_results(
        self,
        state: AgentState,
        output: str,
    ) -> TestSummary:
        """Parse test results from execution output.

        Args:
            state: Current state.
            output: Execution output containing results.

        Returns:
            TestSummary with parsed results.
        """
        # Try to parse structured results from output
        results_match = re.search(
            r"TEST_RESULTS_START\s*(\{.*?\})\s*TEST_RESULTS_END",
            output,
            re.DOTALL,
        )

        if results_match:
            try:
                data = json.loads(results_match.group(1))
                test_results = []
                for failure in data.get("failures", []):
                    test_results.append(
                        TestResult(
                            name=failure.get("test", "unknown"),
                            passed=False,
                            error_message=failure.get("error"),
                            criterion=failure.get("criterion"),
                            stack_trace=failure.get("trace"),
                        )
                    )
                return TestSummary(
                    total=data.get("total", 0),
                    passed=data.get("passed", 0),
                    failed=data.get("failed", 0),
                    errors=data.get("errors", 0),
                    results=test_results,
                )
            except json.JSONDecodeError:
                self._logger.warning("Failed to parse JSON test results")

        # Try to read from JSON report file
        report_path = state.work_dir / self.REPORTS_DIR / self.TEST_RESULTS_FILE
        if report_path.exists():
            return self._parse_json_report(report_path)

        # Parse from pytest output patterns
        return self._parse_pytest_output(output)

    def _parse_json_report(self, report_path: Path) -> TestSummary:
        """Parse pytest JSON report.

        Args:
            report_path: Path to JSON report file.

        Returns:
            TestSummary from report.
        """
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            summary = data.get("summary", {})

            results: list[TestResult] = []
            for test in data.get("tests", []):
                if test.get("outcome") == "failed":
                    results.append(
                        TestResult(
                            name=test.get("nodeid", "unknown"),
                            passed=False,
                            error_message=test.get("call", {}).get("longrepr"),
                            stack_trace=test.get("call", {}).get("longrepr"),
                        )
                    )

            return TestSummary(
                total=summary.get("total", 0),
                passed=summary.get("passed", 0),
                failed=summary.get("failed", 0),
                errors=summary.get("error", 0),
                results=results,
            )
        except Exception as e:
            self._logger.error(f"Failed to parse JSON report: {e}")
            return TestSummary(total=0, passed=0, failed=0, errors=1, results=[])

    def _parse_pytest_output(self, output: str) -> TestSummary:
        """Parse pytest console output.

        Args:
            output: Pytest console output.

        Returns:
            TestSummary parsed from output.
        """
        # Look for summary line like "5 passed, 2 failed, 1 error"
        summary_match = re.search(
            r"(\d+)\s+passed.*?(\d+)\s+failed",
            output,
            re.IGNORECASE,
        )

        if summary_match:
            passed = int(summary_match.group(1))
            failed = int(summary_match.group(2))
            return TestSummary(
                total=passed + failed,
                passed=passed,
                failed=failed,
                errors=0,
                results=[],
            )

        # Check for all passed
        if re.search(r"(\d+)\s+passed", output, re.IGNORECASE):
            match = re.search(r"(\d+)\s+passed", output)
            if match:
                passed = int(match.group(1))
                return TestSummary(
                    total=passed,
                    passed=passed,
                    failed=0,
                    errors=0,
                    results=[],
                )

        # Default - assume success if no failure indicators
        if "FAILED" not in output and "ERROR" not in output:
            return TestSummary(total=1, passed=1, failed=0, errors=0, results=[])

        return TestSummary(total=1, passed=0, failed=1, errors=0, results=[])

    def _generate_bug_report(
        self,
        state: AgentState,
        summary: TestSummary,
        criteria: list[str],
        reports_dir: Path,
    ) -> Path:
        """Generate detailed bug report.

        Args:
            state: Current state.
            summary: Test execution summary.
            criteria: Acceptance criteria.
            reports_dir: Directory for reports.

        Returns:
            Path to generated bug report.
        """
        report_path = reports_dir / self.BUG_REPORT_FILE

        lines = [
            "# QA Bug Report",
            "",
            f"Generated: {datetime.now().isoformat()}",
            f"Project: {state.project_name}",
            "",
            "## Test Execution Summary",
            "",
            f"- **Total Tests**: {summary.total}",
            f"- **Passed**: {summary.passed}",
            f"- **Failed**: {summary.failed}",
            f"- **Errors**: {summary.errors}",
            "",
            "---",
            "",
        ]

        if summary.results:
            lines.append("## Failed Test Details")
            lines.append("")

            for i, result in enumerate(summary.results, 1):
                severity = self._classify_severity(result)
                lines.extend([
                    f"### Bug #{i}: {result.name}",
                    "",
                    f"**Severity**: {severity}",
                    "",
                ])

                if result.criterion:
                    lines.extend([
                        "**Acceptance Criterion**:",
                        f"> {result.criterion}",
                        "",
                    ])

                if result.error_message:
                    lines.extend([
                        "**Error**:",
                        f"```",
                        result.error_message[:500],  # Truncate if too long
                        "```",
                        "",
                    ])

                if result.stack_trace:
                    lines.extend([
                        "**Stack Trace**:",
                        "```",
                        result.stack_trace[:1000],  # Truncate
                        "```",
                        "",
                    ])

                # Add root cause analysis placeholder
                lines.extend([
                    "**Root Cause Analysis**:",
                    "See error details above for investigation.",
                    "",
                    "**Recommended Fix**:",
                    "Review the failing test and implement the expected behavior.",
                    "",
                    "---",
                    "",
                ])

        # Add acceptance criteria mapping
        lines.extend([
            "## Acceptance Criteria Coverage",
            "",
            "| Criterion | Status |",
            "|-----------|--------|",
        ])

        for criterion in criteria:
            # Check if any failure mentions this criterion
            failed = any(
                result.criterion and criterion in result.criterion
                for result in summary.results
            )
            status = "❌ Failed" if failed else "✅ Passed"
            lines.append(f"| {criterion[:50]}... | {status} |")

        lines.append("")

        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path

    def _classify_severity(self, result: TestResult) -> str:
        """Classify bug severity based on test result.

        Args:
            result: The test result.

        Returns:
            Severity level string.
        """
        if result.error_message:
            error_lower = result.error_message.lower()
            # Critical: security, data loss, crash
            if any(
                keyword in error_lower
                for keyword in ["security", "crash", "data loss", "authentication"]
            ):
                return "Critical"
            # High: core functionality
            if any(
                keyword in error_lower
                for keyword in ["error", "exception", "failed", "invalid"]
            ):
                return "High"
            # Medium: business logic issues
            if any(
                keyword in error_lower
                for keyword in ["assert", "expected", "actual"]
            ):
                return "Medium"

        return "Medium"  # Default

    def validate_output(self, artifact_path: Path) -> bool:
        """Validate a QA artifact (bug report or test file).

        Args:
            artifact_path: Path to the artifact.

        Returns:
            True if artifact is valid.
        """
        if not artifact_path.exists():
            return False

        if artifact_path.name == self.BUG_REPORT_FILE:
            return self._validate_bug_report(artifact_path)

        if artifact_path.suffix == ".py":
            # Validate test file syntax
            try:
                content = artifact_path.read_text(encoding="utf-8")
                compile(content, str(artifact_path), "exec")
                return True
            except SyntaxError:
                return False

        return True

    def _validate_bug_report(self, report_path: Path) -> bool:
        """Validate bug report structure.

        Args:
            report_path: Path to bug report.

        Returns:
            True if report is valid.
        """
        content = report_path.read_text(encoding="utf-8")

        # Check for required sections
        required = ["Test Execution Summary", "Total Tests"]
        for section in required:
            if section not in content:
                self._logger.warning(f"Bug report missing section: {section}")
                return False

        return True


def main() -> None:
    """Entry point for testing QA agent standalone."""
    import argparse

    parser = argparse.ArgumentParser(description="QA Agent - Testing & Bug Reports")
    parser.add_argument(
        "--prd",
        type=str,
        help="Path to PRD file",
    )
    parser.add_argument(
        "--work-dir",
        type=str,
        default=".",
        help="Working directory for execution",
    )

    args = parser.parse_args()

    from src.wrappers.state import create_initial_state

    state = create_initial_state(
        mission="Test the implementation",
        work_dir=Path(args.work_dir),
    ).with_update(current_phase="qa")

    if args.prd:
        prd_path = Path(args.prd)
        if prd_path.exists():
            state = state.with_update(path_prd=prd_path)

    agent = QAAgent()
    print(f"QA Agent: {agent.role_description}")
    print("-" * 50)

    try:
        new_state = agent.execute(state)
        print(f"\nExecution completed:")
        print(f"  QA Passed: {new_state.qa_passed}")
        print(f"  Bug Report: {new_state.path_bug_report}")
        print(f"  Phase: {new_state.current_phase}")
    except Exception as e:
        print(f"\nExecution failed: {e}")
        raise


if __name__ == "__main__":
    main()
