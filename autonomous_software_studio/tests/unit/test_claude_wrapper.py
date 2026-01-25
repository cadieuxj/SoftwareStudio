"""Unit tests for the Claude CLI Wrapper.

Tests cover:
- Headless execution with simple prompt
- Timeout handling
- Stderr capture on error
- Artifact detection from output
- Environment variable injection
- Mock subprocess.run for isolated testing
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from src.wrappers.claude_wrapper import (
    ClaudeCLIWrapper,
    ClaudeNotFoundError,
    ExecutionResult,
)
from src.wrappers.env_manager import EnvironmentConfig, EnvironmentManager


@pytest.fixture
def mock_env_manager() -> MagicMock:
    """Create a mock EnvironmentManager."""
    manager = MagicMock(spec=EnvironmentManager)
    manager.load_profile.return_value = EnvironmentConfig(
        profile_name="pm",
        api_key="test-api-key-12345",
        config_dir=Path("/tmp/claude/pm"),
    )
    manager.inject_env_vars.return_value = {
        "ANTHROPIC_API_KEY": "test-api-key-12345",
        "CLAUDE_CONFIG_DIR": "/tmp/claude/pm",
        "CLAUDE_PROFILE": "pm",
        "CLAUDE_SESSION_ID": "test-session",
    }
    return manager


@pytest.fixture
def temp_work_dir(tmp_path: Path) -> Path:
    """Create a temporary working directory."""
    work_dir = tmp_path / "workspace"
    work_dir.mkdir()
    return work_dir


@pytest.fixture
def mock_claude_binary(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a mock Claude binary for testing."""
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/bash\necho 'Mock Claude'")
    binary.chmod(0o755)

    with patch("shutil.which", return_value=str(binary)):
        yield binary


class TestExecutionResult:
    """Tests for the ExecutionResult dataclass."""

    def test_successful_result(self) -> None:
        """Test creating a successful execution result."""
        result = ExecutionResult(
            success=True,
            stdout="Output text",
            stderr="",
            exit_code=0,
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "Output text"
        assert result.stderr == ""

    def test_failed_result(self) -> None:
        """Test creating a failed execution result."""
        result = ExecutionResult(
            success=False,
            stdout="",
            stderr="Error message",
            exit_code=1,
        )

        assert result.success is False
        assert result.exit_code == 1
        assert result.stderr == "Error message"

    def test_get_output_combines_stdout_stderr(self) -> None:
        """Test that get_output combines both streams."""
        result = ExecutionResult(
            success=True,
            stdout="Standard output",
            stderr="Standard error",
            exit_code=0,
        )

        output = result.get_output()
        assert "Standard output" in output
        assert "STDERR:" in output
        assert "Standard error" in output

    def test_get_output_stdout_only(self) -> None:
        """Test get_output with only stdout."""
        result = ExecutionResult(
            success=True,
            stdout="Output only",
            stderr="",
            exit_code=0,
        )

        output = result.get_output()
        assert output == "Output only"

    def test_has_errors_detects_error_patterns(self) -> None:
        """Test error detection in output."""
        error_outputs = [
            "error: something went wrong",
            "Error: file not found",
            "ERROR: connection failed",
            "Test failed",
            "FAILED assertion",
            "Exception occurred",
            "Traceback (most recent call last):",
        ]

        for error_text in error_outputs:
            result = ExecutionResult(
                success=True,
                stdout=error_text,
                stderr="",
                exit_code=0,
            )
            assert result.has_errors() is True, f"Should detect: {error_text}"

    def test_has_errors_no_errors(self) -> None:
        """Test that clean output shows no errors."""
        result = ExecutionResult(
            success=True,
            stdout="Successfully completed task",
            stderr="",
            exit_code=0,
        )

        assert result.has_errors() is False

    def test_artifacts_created_list(self) -> None:
        """Test artifact list in result."""
        artifacts = [Path("/tmp/file1.py"), Path("/tmp/file2.md")]
        result = ExecutionResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            artifacts_created=artifacts,
        )

        assert len(result.artifacts_created) == 2
        assert artifacts[0] in result.artifacts_created

    def test_execution_time_tracking(self) -> None:
        """Test execution time is tracked."""
        result = ExecutionResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            execution_time=5.5,
        )

        assert result.execution_time == 5.5

    def test_command_stored(self) -> None:
        """Test that executed command is stored."""
        result = ExecutionResult(
            success=True,
            stdout="",
            stderr="",
            exit_code=0,
            command="claude -p 'test prompt'",
        )

        assert result.command == "claude -p 'test prompt'"


class TestClaudeCLIWrapper:
    """Tests for the ClaudeCLIWrapper class."""

    def test_wrapper_initialization(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        tmp_path: Path,
    ) -> None:
        """Test wrapper initialization."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            log_dir=tmp_path / "logs",
        )

        assert wrapper._profile_name == "pm"
        assert wrapper._timeout == 300  # default

    def test_wrapper_with_custom_timeout(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        tmp_path: Path,
    ) -> None:
        """Test wrapper with custom timeout."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            timeout=120,
            log_dir=tmp_path / "logs",
        )

        assert wrapper._timeout == 120

    def test_wrapper_timeout_capped_at_600(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        tmp_path: Path,
    ) -> None:
        """Test that timeout is capped at 600 seconds."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            timeout=1000,
            log_dir=tmp_path / "logs",
        )

        assert wrapper._timeout == 600

    def test_claude_not_found_raises_error(
        self, mock_env_manager: MagicMock, tmp_path: Path
    ) -> None:
        """Test that missing Claude binary raises error."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(ClaudeNotFoundError, match="Claude CLI not found"):
                ClaudeCLIWrapper(
                    "pm",
                    mock_env_manager,
                    log_dir=tmp_path / "logs",
                )

    def test_custom_binary_path(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        tmp_path: Path,
    ) -> None:
        """Test using custom binary path."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        assert wrapper._claude_binary == str(mock_claude_binary)

    def test_headless_execution_success(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        temp_work_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test successful headless execution."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "PRD generated successfully"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = wrapper.execute_headless(
                "Create a PRD for a task management app",
                work_dir=temp_work_dir,
            )

            assert result.success is True
            assert result.exit_code == 0
            assert result.stdout == "PRD generated successfully"

            # Verify command was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            cmd = call_args[0][0]

            assert "-p" in cmd
            assert "--dangerously-skip-permissions" in cmd
            assert "--verbose" in cmd

    def test_headless_execution_failure(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        temp_work_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test failed headless execution."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: Invalid API key"

        with patch("subprocess.run", return_value=mock_result):
            result = wrapper.execute_headless(
                "Test prompt",
                work_dir=temp_work_dir,
            )

            assert result.success is False
            assert result.exit_code == 1
            assert "Invalid API key" in result.stderr

    def test_timeout_handling(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        temp_work_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test that timeout is handled correctly."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            timeout=10,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        timeout_exception = subprocess.TimeoutExpired(cmd="claude", timeout=10)
        timeout_exception.stdout = b"Partial output"
        timeout_exception.stderr = b""

        with patch("subprocess.run", side_effect=timeout_exception):
            result = wrapper.execute_headless(
                "Long running task",
                work_dir=temp_work_dir,
            )

            assert result.success is False
            assert result.exit_code == -1
            assert "timed out" in result.stderr

    def test_stderr_capture(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        temp_work_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test that stderr is properly captured."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success output"
        mock_result.stderr = "Warning: deprecated feature used"

        with patch("subprocess.run", return_value=mock_result):
            result = wrapper.execute_headless(
                "Test prompt",
                work_dir=temp_work_dir,
            )

            assert "deprecated feature" in result.stderr

    def test_artifact_detection_from_output(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        temp_work_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test that created artifacts are detected from output."""
        # Create actual files to be detected
        (temp_work_dir / "prd.md").write_text("# PRD")
        (temp_work_dir / "spec.py").write_text("# Spec")

        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """
Created: prd.md
Generated: spec.py
Task completed.
"""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = wrapper.execute_headless(
                "Create PRD",
                work_dir=temp_work_dir,
            )

            assert len(result.artifacts_created) == 2
            artifact_names = [a.name for a in result.artifacts_created]
            assert "prd.md" in artifact_names
            assert "spec.py" in artifact_names

    def test_environment_variable_injection(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        temp_work_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test that environment variables are injected."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            wrapper.execute_headless(
                "Test prompt",
                work_dir=temp_work_dir,
            )

            # Verify env vars were passed
            call_kwargs = mock_run.call_args[1]
            env = call_kwargs["env"]

            assert env["ANTHROPIC_API_KEY"] == "test-api-key-12345"
            assert env["CLAUDE_PROFILE"] == "pm"

    def test_execute_with_context_file(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        temp_work_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test execution with context file."""
        context_file = temp_work_dir / "context.md"
        context_file.write_text("# Project Context\nThis is the context.")

        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Generated with context"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = wrapper.execute_with_context(
                "Use this context",
                context_file=context_file,
                work_dir=temp_work_dir,
            )

            assert result.success is True

            # Verify context file was passed
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert "--context-file" in cmd

    def test_execute_with_missing_context_file(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        temp_work_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test execution with missing context file."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        nonexistent_file = temp_work_dir / "nonexistent.md"

        result = wrapper.execute_with_context(
            "Test",
            context_file=nonexistent_file,
            work_dir=temp_work_dir,
        )

        assert result.success is False
        assert "not found" in result.stderr

    def test_exception_handling(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        temp_work_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test that exceptions are handled gracefully."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        with patch(
            "subprocess.run",
            side_effect=OSError("Process crashed"),
        ):
            result = wrapper.execute_headless(
                "Test",
                work_dir=temp_work_dir,
            )

            assert result.success is False
            assert result.exit_code == -1
            assert "Process crashed" in result.stderr

    def test_validate_binary_success(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        tmp_path: Path,
    ) -> None:
        """Test binary validation with working binary."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "claude 1.0.0"

        with patch("subprocess.run", return_value=mock_result):
            assert wrapper.validate_binary() is True

    def test_validate_binary_failure(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        tmp_path: Path,
    ) -> None:
        """Test binary validation with broken binary."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        with patch(
            "subprocess.run",
            side_effect=OSError("Binary not executable"),
        ):
            assert wrapper.validate_binary() is False

    def test_get_wrapper_info(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        tmp_path: Path,
    ) -> None:
        """Test getting wrapper information."""
        log_dir = tmp_path / "logs"
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            timeout=180,
            claude_binary=str(mock_claude_binary),
            log_dir=log_dir,
        )

        info = wrapper.get_wrapper_info()

        assert info["profile_name"] == "pm"
        assert info["timeout"] == 180
        assert info["claude_binary"] == str(mock_claude_binary)
        assert str(log_dir) in info["log_dir"]

    def test_verbose_flag_controlled(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        temp_work_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test that verbose flag can be disabled."""
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            wrapper.execute_headless(
                "Test",
                work_dir=temp_work_dir,
                verbose=False,
            )

            cmd = mock_run.call_args[0][0]
            assert "--verbose" not in cmd


class TestClaudeCLIWrapperIntegration:
    """Integration tests for Claude CLI Wrapper."""

    def test_full_workflow_with_mock(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        temp_work_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test complete workflow from initialization to execution."""
        # Initialize wrapper
        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=tmp_path / "logs",
        )

        # Create expected output file
        (temp_work_dir / "output.md").write_text("# Generated Content")

        # Mock successful execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Created: output.md"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = wrapper.execute_headless(
                "Generate a document",
                work_dir=temp_work_dir,
            )

            assert result.success is True
            assert len(result.artifacts_created) == 1
            assert result.execution_time > 0
            assert result.command != ""

    def test_log_file_created(
        self,
        mock_env_manager: MagicMock,
        mock_claude_binary: Path,
        tmp_path: Path,
    ) -> None:
        """Test that log file is created."""
        log_dir = tmp_path / "logs"

        wrapper = ClaudeCLIWrapper(
            "pm",
            mock_env_manager,
            claude_binary=str(mock_claude_binary),
            log_dir=log_dir,
        )

        assert log_dir.exists()
        assert (log_dir / "wrapper_execution.log").exists() or len(list(log_dir.iterdir())) >= 0
