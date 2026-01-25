"""Claude CLI Wrapper for programmatic control of claude-code.

This module provides a wrapper around the Claude CLI tool, enabling
programmatic execution of Claude in headless mode with proper environment
isolation for multi-agent orchestration.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.wrappers.env_manager import EnvironmentConfig, EnvironmentManager


class ClaudeNotFoundError(Exception):
    """Raised when the Claude CLI binary is not found."""

    pass


class ExecutionTimeoutError(Exception):
    """Raised when command execution times out."""

    pass


class ExecutionError(Exception):
    """Raised when command execution fails."""

    pass


@dataclass
class ExecutionResult:
    """Result of a Claude CLI execution.

    Attributes:
        success: Whether the execution completed successfully.
        stdout: Standard output from the command.
        stderr: Standard error from the command.
        exit_code: The process exit code.
        artifacts_created: List of file paths created during execution.
        execution_time: Time taken to execute in seconds.
        command: The command that was executed.
    """

    success: bool
    stdout: str
    stderr: str
    exit_code: int
    artifacts_created: list[Path] = field(default_factory=list)
    execution_time: float = 0.0
    command: str = ""

    def get_output(self) -> str:
        """Get combined stdout and stderr output.

        Returns:
            Combined output string.
        """
        output_parts = []
        if self.stdout:
            output_parts.append(self.stdout)
        if self.stderr:
            output_parts.append(f"STDERR:\n{self.stderr}")
        return "\n".join(output_parts)

    def has_errors(self) -> bool:
        """Check if there are any error indicators in output.

        Returns:
            True if errors detected, False otherwise.
        """
        error_patterns = [
            r"error:",
            r"Error:",
            r"ERROR:",
            r"failed",
            r"Failed",
            r"FAILED",
            r"exception",
            r"Exception",
            r"traceback",
            r"Traceback",
        ]
        combined = self.get_output().lower()
        return any(re.search(pattern.lower(), combined) for pattern in error_patterns)


class ClaudeCLIWrapper:
    """Wrapper for programmatic control of the Claude CLI.

    This class handles:
    - Headless execution with proper flags
    - Environment variable injection per profile
    - Output capture and parsing
    - Timeout and error handling
    - Artifact detection from output

    Example:
        >>> env_manager = EnvironmentManager()
        >>> wrapper = ClaudeCLIWrapper("pm", env_manager)
        >>> result = wrapper.execute_headless("Create a PRD for task management app")
        >>> print(result.stdout)
    """

    # Default paths to search for Claude CLI
    CLAUDE_BINARY_NAMES = ["claude", "claude-code"]

    # Default execution timeout in seconds
    DEFAULT_TIMEOUT = 300

    # Patterns to detect created artifacts in output
    ARTIFACT_PATTERNS = [
        r"(?:Created|Wrote|Generated|Saved):\s*([^\s]+\.(?:py|js|ts|md|json|yaml|yml|txt))",
        r"(?:File created|Writing to):\s*([^\s]+)",
        r"→\s*([^\s]+\.(?:py|js|ts|md|json|yaml|yml|txt))",
    ]

    def __init__(
        self,
        profile_name: str,
        env_manager: EnvironmentManager,
        timeout: int = DEFAULT_TIMEOUT,
        claude_binary: str | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize the Claude CLI wrapper.

        Args:
            profile_name: The profile to use (pm, arch, eng, qa).
            env_manager: The EnvironmentManager instance for configuration.
            timeout: Execution timeout in seconds (max 600).
            claude_binary: Optional path to Claude binary. Auto-detected if not provided.
            log_dir: Directory for execution logs. Defaults to ./logs.

        Raises:
            ClaudeNotFoundError: If Claude binary cannot be found.
        """
        self._profile_name = profile_name
        self._env_manager = env_manager
        self._timeout = min(timeout, 600)  # Cap at 10 minutes
        self._config: EnvironmentConfig | None = None
        self._log_dir = log_dir or Path("logs")
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging
        self._logger = self._setup_logger()

        # Find and validate Claude binary
        self._claude_binary = claude_binary or self._find_claude_binary()

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for wrapper execution.

        Returns:
            Configured logger instance.
        """
        logger = logging.getLogger(f"claude_wrapper.{self._profile_name}")
        logger.setLevel(logging.DEBUG)

        # File handler
        log_file = self._log_dir / "wrapper_execution.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        # Avoid duplicate handlers
        if not logger.handlers:
            logger.addHandler(file_handler)

        return logger

    def _find_claude_binary(self) -> str:
        """Find the Claude CLI binary.

        Returns:
            Path to the Claude binary.

        Raises:
            ClaudeNotFoundError: If binary cannot be found.
        """
        for binary_name in self.CLAUDE_BINARY_NAMES:
            path = shutil.which(binary_name)
            if path:
                self._logger.info(f"Found Claude binary at: {path}")
                return path

        # Check common installation paths
        common_paths = [
            Path.home() / ".local" / "bin" / "claude",
            Path("/usr/local/bin/claude"),
            Path("/usr/bin/claude"),
        ]

        for path in common_paths:
            if path.exists() and path.is_file():
                self._logger.info(f"Found Claude binary at: {path}")
                return str(path)

        self._logger.warning("Claude binary not found in PATH or common locations")
        raise ClaudeNotFoundError(
            "Claude CLI not found. Please install claude-code or provide path via claude_binary parameter."
        )

    def _get_config(self) -> EnvironmentConfig:
        """Get or load the environment configuration.

        Returns:
            The EnvironmentConfig for this wrapper's profile.
        """
        if self._config is None:
            self._config = self._env_manager.load_profile(self._profile_name)
        return self._config

    def _build_command(
        self,
        prompt: str,
        work_dir: Path | None = None,
        context_file: Path | None = None,
        verbose: bool = True,
    ) -> list[str]:
        """Build the Claude CLI command with appropriate flags.

        Args:
            prompt: The prompt to send to Claude.
            work_dir: Working directory for execution.
            context_file: Optional file to include as context.
            verbose: Whether to enable verbose output.

        Returns:
            List of command arguments.
        """
        cmd = [self._claude_binary]

        # Headless mode with prompt
        cmd.extend(["-p", prompt])

        # Skip permission prompts for autonomous operation
        cmd.append("--dangerously-skip-permissions")

        # Verbose output for debugging
        if verbose:
            cmd.append("--verbose")

        # Set working directory
        if work_dir:
            cmd.extend(["--cwd", str(work_dir)])

        # Include context file if provided
        if context_file and context_file.exists():
            cmd.extend(["--context-file", str(context_file)])

        return cmd

    def execute_headless(
        self,
        prompt: str,
        work_dir: Path | None = None,
        verbose: bool = True,
    ) -> ExecutionResult:
        """Execute Claude in headless mode with a prompt.

        Args:
            prompt: The prompt to send to Claude.
            work_dir: Working directory for execution. Defaults to current directory.
            verbose: Whether to enable verbose output.

        Returns:
            ExecutionResult containing output and status.

        Raises:
            ExecutionTimeoutError: If execution exceeds timeout.
            ExecutionError: If execution fails unexpectedly.
        """
        work_dir = work_dir or Path.cwd()
        work_dir = work_dir.resolve()

        # Build command
        cmd = self._build_command(prompt, work_dir, verbose=verbose)
        cmd_str = " ".join(cmd)

        self._logger.info(f"Executing command: {cmd_str}")
        self._logger.info(f"Working directory: {work_dir}")

        # Get environment variables
        config = self._get_config()
        env_vars = self._env_manager.inject_env_vars(config)

        start_time = datetime.now()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                env=env_vars,
                cwd=work_dir,
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            # Parse artifacts from output
            artifacts = self._parse_artifacts(result.stdout, work_dir)

            exec_result = ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                artifacts_created=artifacts,
                execution_time=execution_time,
                command=cmd_str,
            )

            self._logger.info(
                f"Execution completed: success={exec_result.success}, "
                f"exit_code={exec_result.exit_code}, "
                f"time={execution_time:.2f}s"
            )

            return exec_result

        except subprocess.TimeoutExpired as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._logger.error(f"Execution timed out after {self._timeout}s")

            # Try to capture partial output
            stdout = e.stdout.decode() if e.stdout else ""
            stderr = e.stderr.decode() if e.stderr else ""

            return ExecutionResult(
                success=False,
                stdout=stdout,
                stderr=stderr + f"\nExecution timed out after {self._timeout} seconds",
                exit_code=-1,
                execution_time=execution_time,
                command=cmd_str,
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._logger.exception(f"Execution failed with exception: {e}")

            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time=execution_time,
                command=cmd_str,
            )

    def execute_with_context(
        self,
        prompt: str,
        context_file: Path,
        work_dir: Path | None = None,
        verbose: bool = True,
    ) -> ExecutionResult:
        """Execute Claude with additional context from a file.

        Args:
            prompt: The prompt to send to Claude.
            context_file: Path to file containing additional context.
            work_dir: Working directory for execution.
            verbose: Whether to enable verbose output.

        Returns:
            ExecutionResult containing output and status.
        """
        work_dir = work_dir or Path.cwd()
        work_dir = work_dir.resolve()

        if not context_file.exists():
            self._logger.warning(f"Context file not found: {context_file}")
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Context file not found: {context_file}",
                exit_code=1,
                command="",
            )

        # Build command with context file
        cmd = self._build_command(prompt, work_dir, context_file, verbose)
        cmd_str = " ".join(cmd)

        self._logger.info(f"Executing command with context: {cmd_str}")
        self._logger.info(f"Context file: {context_file}")

        # Get environment variables
        config = self._get_config()
        env_vars = self._env_manager.inject_env_vars(config)

        start_time = datetime.now()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                env=env_vars,
                cwd=work_dir,
            )

            execution_time = (datetime.now() - start_time).total_seconds()
            artifacts = self._parse_artifacts(result.stdout, work_dir)

            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                artifacts_created=artifacts,
                execution_time=execution_time,
                command=cmd_str,
            )

        except subprocess.TimeoutExpired:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {self._timeout} seconds",
                exit_code=-1,
                execution_time=execution_time,
                command=cmd_str,
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time=execution_time,
                command=cmd_str,
            )

    def capture_output(self) -> tuple[str, str]:
        """Capture stdout and stderr from the last execution.

        This is a convenience method for getting output from
        the most recent execution.

        Returns:
            Tuple of (stdout, stderr) strings.
        """
        # This would require storing last result
        # For now, return empty - users should use ExecutionResult
        return ("", "")

    def _parse_artifacts(self, output: str, work_dir: Path) -> list[Path]:
        """Parse output to detect created artifacts.

        Args:
            output: The stdout from execution.
            work_dir: The working directory for resolving relative paths.

        Returns:
            List of detected artifact paths.
        """
        artifacts: list[Path] = []

        for pattern in self.ARTIFACT_PATTERNS:
            matches = re.findall(pattern, output, re.MULTILINE)
            for match in matches:
                path = Path(match)
                if not path.is_absolute():
                    path = work_dir / path

                # Only include if file actually exists
                if path.exists():
                    artifacts.append(path.resolve())

        # Remove duplicates while preserving order
        seen: set[Path] = set()
        unique_artifacts: list[Path] = []
        for artifact in artifacts:
            if artifact not in seen:
                seen.add(artifact)
                unique_artifacts.append(artifact)

        return unique_artifacts

    def validate_binary(self) -> bool:
        """Validate that the Claude binary is executable.

        Returns:
            True if binary is valid, False otherwise.
        """
        try:
            result = subprocess.run(
                [self._claude_binary, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._logger.info(f"Claude version: {result.stdout.strip()}")
            return result.returncode == 0
        except Exception as e:
            self._logger.error(f"Binary validation failed: {e}")
            return False

    def get_wrapper_info(self) -> dict[str, Any]:
        """Get information about this wrapper instance.

        Returns:
            Dictionary containing wrapper configuration.
        """
        return {
            "profile_name": self._profile_name,
            "claude_binary": self._claude_binary,
            "timeout": self._timeout,
            "log_dir": str(self._log_dir),
            "config_loaded": self._config is not None,
        }


def main() -> None:
    """Entry point for testing the Claude wrapper."""
    import json

    print("Claude CLI Wrapper - Test Mode")
    print("-" * 40)

    try:
        env_manager = EnvironmentManager()
        wrapper = ClaudeCLIWrapper("pm", env_manager)

        info = wrapper.get_wrapper_info()
        print("Wrapper Info:")
        print(json.dumps(info, indent=2))

        # Validate binary
        if wrapper.validate_binary():
            print("\nClaude binary validated successfully!")
        else:
            print("\nClaude binary validation failed.")

    except ClaudeNotFoundError as e:
        print(f"\nNote: {e}")
        print("Tests can still run with mocked subprocess.")


if __name__ == "__main__":
    main()
