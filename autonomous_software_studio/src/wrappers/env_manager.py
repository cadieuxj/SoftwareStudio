"""Environment Configuration Manager for multi-account identity management.

This module provides the infrastructure for managing multiple Claude API profiles,
each with isolated configuration directories and API keys. It supports the
multi-agent orchestration pipeline by ensuring clean environment separation
between different agent personas (PM, Architect, Engineer, QA).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from dotenv import load_dotenv

from src.config.agent_settings import AgentSettingsManager


class ProfileNotFoundError(Exception):
    """Raised when a requested profile does not exist."""

    pass


class InvalidAPIKeyError(Exception):
    """Raised when an API key is missing or invalid."""

    pass


class ConfigurationError(Exception):
    """Raised when there is a configuration error."""

    pass


@dataclass
class EnvironmentConfig:
    """Configuration for a single Claude agent profile.

    Attributes:
        profile_name: Name of the profile (pm, arch, eng, qa).
        api_key: The API key for this profile.
        config_dir: Path to the configuration directory for this profile.
        session_id: Unique identifier for the current session.
    """

    profile_name: str
    api_key: str | None
    config_dir: Path
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    require_api_key: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize configuration after initialization."""
        if not self.profile_name:
            raise ConfigurationError("Profile name cannot be empty")
        if self.require_api_key and not self.api_key:
            raise InvalidAPIKeyError(
                f"API key for profile '{self.profile_name}' is missing or empty"
            )
        # Ensure config_dir is a Path object
        if isinstance(self.config_dir, str):
            self.config_dir = Path(self.config_dir)
        # Expand user home directory
        self.config_dir = self.config_dir.expanduser().resolve()


class EnvironmentManager:
    """Manages environment configurations for multiple Claude agent profiles.

    This class handles loading, validating, and injecting environment variables
    for different agent profiles. Each profile has its own API key and
    configuration directory to ensure complete isolation.

    Attributes:
        PROFILE_MAPPING: Mapping of profile names to their environment variable
            names and default configuration directories.

    Example:
        >>> manager = EnvironmentManager()
        >>> config = manager.load_profile("pm")
        >>> env_vars = manager.inject_env_vars(config)
        >>> print(env_vars["ANTHROPIC_API_KEY"])
    """

    PROFILE_MAPPING: ClassVar[dict[str, dict[str, str]]] = {
        "pm": {
            "key_var": "ANTHROPIC_API_KEY_PM",
            "config_dir": "~/.claude/pm",
        },
        "arch": {
            "key_var": "ANTHROPIC_API_KEY_ARCH",
            "config_dir": "~/.claude/arch",
        },
        "eng": {
            "key_var": "ANTHROPIC_API_KEY_ENG",
            "config_dir": "~/.claude/eng",
        },
        "qa": {
            "key_var": "ANTHROPIC_API_KEY_QA",
            "config_dir": "~/.claude/qa",
        },
    }

    # Additional environment variables from Table 1
    COMMON_ENV_VARS: ClassVar[list[str]] = [
        "ANTHROPIC_API_KEY",
        "CLAUDE_CONFIG_DIR",
        "CLAUDE_MODEL",
        "CLAUDE_MAX_TOKENS",
        "CLAUDE_TEMPERATURE",
        "LOG_LEVEL",
        "LANGGRAPH_API_KEY",
        "STREAMLIT_SERVER_PORT",
    ]

    def __init__(self, env_file: Path | None = None) -> None:
        """Initialize the EnvironmentManager.

        Args:
            env_file: Optional path to a .env file. If not provided, will
                search for .env in the current directory and parent directories.
        """
        self._env_file = env_file
        self._loaded = False
        self._configs: dict[str, EnvironmentConfig] = {}
        self._load_dotenv()

    def _load_dotenv(self) -> None:
        """Load environment variables from .env file."""
        if self._env_file:
            load_dotenv(self._env_file)
        else:
            load_dotenv()
        self._loaded = True

    def validate_profile_exists(self, profile_name: str) -> bool:
        """Check if a profile name is valid.

        Args:
            profile_name: The name of the profile to validate.

        Returns:
            True if the profile exists in PROFILE_MAPPING, False otherwise.
        """
        return profile_name.lower() in self.PROFILE_MAPPING

    def load_profile(self, profile_name: str) -> EnvironmentConfig:
        """Load configuration for a specific profile.

        Args:
            profile_name: The name of the profile to load (pm, arch, eng, qa).

        Returns:
            An EnvironmentConfig instance with the profile's configuration.

        Raises:
            ProfileNotFoundError: If the profile name is not recognized.
            InvalidAPIKeyError: If the API key for the profile is missing.
        """
        profile_name = profile_name.lower()

        if not self.validate_profile_exists(profile_name):
            valid_profiles = ", ".join(self.PROFILE_MAPPING.keys())
            raise ProfileNotFoundError(
                f"Profile '{profile_name}' not found. "
                f"Valid profiles are: {valid_profiles}"
            )

        # Check cache first
        if profile_name in self._configs:
            return self._configs[profile_name]

        mapping = self.PROFILE_MAPPING[profile_name]
        key_var = mapping["key_var"]
        config_dir_str = mapping["config_dir"]

        settings_manager = AgentSettingsManager()
        agent_settings = settings_manager.get_agent(profile_name)
        auth_type = agent_settings.get("auth_type", "api_key")

        # Get API key from settings or environment
        api_key = agent_settings.get("api_key", "") or ""
        if not api_key and auth_type == "api_key":
            api_key = os.getenv(key_var, "")
        if not api_key and auth_type == "api_key":
            legacy_key_var = f"CLAUDE_API_KEY_{profile_name.upper()}"
            api_key = os.getenv(legacy_key_var, "")
        if not api_key and auth_type == "api_key":
            api_key = os.getenv("ANTHROPIC_API_KEY", "")

        if auth_type == "api_key" and not api_key:
            raise InvalidAPIKeyError(
                f"API key not found for profile '{profile_name}'. "
                f"Please set the {key_var} or ANTHROPIC_API_KEY environment variable "
                "or configure it in agent settings."
            )

        # Expand environment variables in config_dir
        config_dir_override = agent_settings.get("claude_profile_dir", "")
        config_dir = self._expand_path(config_dir_override or config_dir_str)

        config = EnvironmentConfig(
            profile_name=profile_name,
            api_key=api_key,
            config_dir=config_dir,
            require_api_key=auth_type == "api_key",
        )

        # Cache the configuration
        self._configs[profile_name] = config

        return config

    def _expand_path(self, path_str: str) -> Path:
        """Expand environment variables and user home in path strings.

        Args:
            path_str: A path string potentially containing ~ or $VAR.

        Returns:
            An expanded and resolved Path object.
        """
        # Expand environment variables first
        expanded = os.path.expandvars(path_str)
        # Then expand user home directory
        path = Path(expanded).expanduser()
        return path.resolve()

    def inject_env_vars(self, config: EnvironmentConfig) -> dict[str, str]:
        """Create a dictionary of environment variables for subprocess execution.

        Args:
            config: The EnvironmentConfig to use for injection.

        Returns:
            A dictionary of environment variables to be passed to subprocess.
        """
        # Start with a copy of current environment
        env_vars = os.environ.copy()

        # Inject profile-specific variables
        if config.api_key:
            env_vars["ANTHROPIC_API_KEY"] = config.api_key
        env_vars["CLAUDE_CONFIG_DIR"] = str(config.config_dir)
        env_vars["CLAUDE_PROFILE"] = config.profile_name
        env_vars["CLAUDE_SESSION_ID"] = config.session_id

        # Ensure config directory exists
        config.config_dir.mkdir(parents=True, exist_ok=True)

        settings_manager = AgentSettingsManager()
        return settings_manager.apply_env_overrides(config.profile_name, env_vars)

    def ensure_config_dirs(self) -> dict[str, Path]:
        """Ensure all profile configuration directories exist.

        Returns:
            A dictionary mapping profile names to their config directory paths.
        """
        dirs: dict[str, Path] = {}
        for profile_name, mapping in self.PROFILE_MAPPING.items():
            config_dir = self._expand_path(mapping["config_dir"])
            config_dir.mkdir(parents=True, exist_ok=True)
            dirs[profile_name] = config_dir
        return dirs

    def get_all_profiles(self) -> list[str]:
        """Get a list of all available profile names.

        Returns:
            A list of valid profile names.
        """
        return list(self.PROFILE_MAPPING.keys())

    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        self._configs.clear()

    def get_env_summary(self) -> dict[str, Any]:
        """Get a summary of the current environment configuration.

        Returns:
            A dictionary containing environment status information.
        """
        summary: dict[str, Any] = {
            "loaded": self._loaded,
            "env_file": str(self._env_file) if self._env_file else "default",
            "profiles": {},
        }

        for profile_name in self.PROFILE_MAPPING:
            mapping = self.PROFILE_MAPPING[profile_name]
            key_var = mapping["key_var"]
            has_key = bool(os.getenv(key_var)) or bool(os.getenv("ANTHROPIC_API_KEY"))
            config_dir = self._expand_path(mapping["config_dir"])

            summary["profiles"][profile_name] = {
                "key_var": key_var,
                "has_key": has_key,
                "config_dir": str(config_dir),
                "config_dir_exists": config_dir.exists(),
            }

        return summary


def main() -> None:
    """Entry point for testing the environment manager."""
    import json

    manager = EnvironmentManager()
    summary = manager.get_env_summary()
    print("Environment Configuration Summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
