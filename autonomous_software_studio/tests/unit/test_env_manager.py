"""Unit tests for the Environment Configuration Manager.

Tests cover:
- Profile loading with valid configuration
- Profile loading with missing API key
- Environment variable injection format
- Profile validation (existing vs non-existing)
- Path expansion and creation
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

from src.wrappers.env_manager import (
    ConfigurationError,
    EnvironmentConfig,
    EnvironmentManager,
    InvalidAPIKeyError,
    ProfileNotFoundError,
)


@pytest.fixture
def temp_env_file(tmp_path: Path) -> Path:
    """Create a temporary .env file with test configuration."""
    env_file = tmp_path / ".env"
    env_content = """
# Test environment configuration
CLAUDE_API_KEY_PM=test-pm-key-12345
CLAUDE_API_KEY_ARCH=test-arch-key-12345
CLAUDE_API_KEY_ENG=test-eng-key-12345
CLAUDE_API_KEY_QA=test-qa-key-12345
ANTHROPIC_API_KEY=test-shared-key-12345
CLAUDE_MODEL=claude-3-sonnet
LOG_LEVEL=DEBUG
"""
    env_file.write_text(env_content)
    return env_file


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Provide a clean environment without Claude-related variables."""
    # Store original values
    original_env = {}
    vars_to_clear = [
        "CLAUDE_API_KEY_PM",
        "CLAUDE_API_KEY_ARCH",
        "CLAUDE_API_KEY_ENG",
        "CLAUDE_API_KEY_QA",
        "ANTHROPIC_API_KEY",
        "CLAUDE_CONFIG_DIR",
        "CLAUDE_PROFILE",
        "CLAUDE_SESSION_ID",
    ]

    for var in vars_to_clear:
        original_env[var] = os.environ.pop(var, None)

    yield

    # Restore original values
    for var, value in original_env.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]


class TestEnvironmentConfig:
    """Tests for the EnvironmentConfig dataclass."""

    def test_valid_config_creation(self, tmp_path: Path) -> None:
        """Test creating a valid EnvironmentConfig."""
        config = EnvironmentConfig(
            profile_name="pm",
            api_key="test-api-key",
            config_dir=tmp_path / "config",
        )

        assert config.profile_name == "pm"
        assert config.api_key == "test-api-key"
        assert config.config_dir == (tmp_path / "config").resolve()
        assert len(config.session_id) == 8  # Default UUID prefix

    def test_config_with_custom_session_id(self, tmp_path: Path) -> None:
        """Test creating config with custom session ID."""
        config = EnvironmentConfig(
            profile_name="arch",
            api_key="test-key",
            config_dir=tmp_path,
            session_id="custom-id",
        )

        assert config.session_id == "custom-id"

    def test_empty_profile_name_raises_error(self, tmp_path: Path) -> None:
        """Test that empty profile name raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Profile name cannot be empty"):
            EnvironmentConfig(
                profile_name="",
                api_key="test-key",
                config_dir=tmp_path,
            )

    def test_empty_api_key_raises_error(self, tmp_path: Path) -> None:
        """Test that empty API key raises InvalidAPIKeyError."""
        with pytest.raises(InvalidAPIKeyError, match="missing or empty"):
            EnvironmentConfig(
                profile_name="pm",
                api_key="",
                config_dir=tmp_path,
            )

    def test_path_string_converted_to_path(self) -> None:
        """Test that string paths are converted to Path objects."""
        config = EnvironmentConfig(
            profile_name="eng",
            api_key="test-key",
            config_dir="/tmp/test",  # type: ignore[arg-type]
        )

        assert isinstance(config.config_dir, Path)

    def test_home_directory_expansion(self) -> None:
        """Test that ~ is expanded in config_dir."""
        config = EnvironmentConfig(
            profile_name="qa",
            api_key="test-key",
            config_dir=Path("~/.claude/qa"),
        )

        assert "~" not in str(config.config_dir)
        assert config.config_dir.is_absolute()


class TestEnvironmentManager:
    """Tests for the EnvironmentManager class."""

    def test_validate_existing_profile(self) -> None:
        """Test validation of existing profiles."""
        manager = EnvironmentManager()

        assert manager.validate_profile_exists("pm") is True
        assert manager.validate_profile_exists("arch") is True
        assert manager.validate_profile_exists("eng") is True
        assert manager.validate_profile_exists("qa") is True

    def test_validate_non_existing_profile(self) -> None:
        """Test validation of non-existing profiles."""
        manager = EnvironmentManager()

        assert manager.validate_profile_exists("invalid") is False
        assert manager.validate_profile_exists("developer") is False
        assert manager.validate_profile_exists("") is False

    def test_validate_profile_case_insensitive(self) -> None:
        """Test that profile validation is case-insensitive."""
        manager = EnvironmentManager()

        assert manager.validate_profile_exists("PM") is True
        assert manager.validate_profile_exists("Arch") is True
        assert manager.validate_profile_exists("ENG") is True

    def test_load_profile_valid(
        self, temp_env_file: Path, clean_env: None, tmp_path: Path
    ) -> None:
        """Test loading a valid profile with API key set."""
        manager = EnvironmentManager(env_file=temp_env_file)
        config = manager.load_profile("pm")

        assert config.profile_name == "pm"
        assert config.api_key == "test-pm-key-12345"
        assert isinstance(config.config_dir, Path)

    def test_load_profile_missing_api_key(
        self, clean_env: None, tmp_path: Path
    ) -> None:
        """Test that loading profile without API key raises error."""
        # Create empty env file
        env_file = tmp_path / ".env"
        env_file.write_text("# Empty config\n")

        manager = EnvironmentManager(env_file=env_file)

        with pytest.raises(InvalidAPIKeyError, match="API key not found"):
            manager.load_profile("pm")

    def test_load_profile_not_found(self) -> None:
        """Test that loading non-existent profile raises error."""
        manager = EnvironmentManager()

        with pytest.raises(ProfileNotFoundError, match="not found"):
            manager.load_profile("nonexistent")

    def test_load_profile_uses_shared_key(
        self, clean_env: None, tmp_path: Path
    ) -> None:
        """Test fallback to ANTHROPIC_API_KEY when profile key not set."""
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=shared-test-key\n")

        manager = EnvironmentManager(env_file=env_file)
        config = manager.load_profile("pm")

        assert config.api_key == "shared-test-key"

    def test_load_profile_caching(
        self, temp_env_file: Path, clean_env: None
    ) -> None:
        """Test that profiles are cached after first load."""
        manager = EnvironmentManager(env_file=temp_env_file)

        config1 = manager.load_profile("pm")
        config2 = manager.load_profile("pm")

        assert config1 is config2  # Same object reference

    def test_inject_env_vars_format(
        self, temp_env_file: Path, clean_env: None, tmp_path: Path
    ) -> None:
        """Test environment variable injection format."""
        manager = EnvironmentManager(env_file=temp_env_file)
        config = manager.load_profile("pm")

        env_vars = manager.inject_env_vars(config)

        assert env_vars["ANTHROPIC_API_KEY"] == config.api_key
        assert env_vars["CLAUDE_CONFIG_DIR"] == str(config.config_dir)
        assert env_vars["CLAUDE_PROFILE"] == "pm"
        assert "CLAUDE_SESSION_ID" in env_vars

    def test_inject_env_vars_creates_config_dir(
        self, temp_env_file: Path, clean_env: None, tmp_path: Path
    ) -> None:
        """Test that inject_env_vars creates config directory."""
        manager = EnvironmentManager(env_file=temp_env_file)

        # Create config with non-existent directory
        config = EnvironmentConfig(
            profile_name="test",
            api_key="test-key",
            config_dir=tmp_path / "new_config_dir",
        )

        assert not config.config_dir.exists()

        manager.inject_env_vars(config)

        assert config.config_dir.exists()
        assert config.config_dir.is_dir()

    def test_inject_env_vars_preserves_existing(
        self, temp_env_file: Path, clean_env: None
    ) -> None:
        """Test that existing environment variables are preserved."""
        os.environ["EXISTING_VAR"] = "existing-value"

        manager = EnvironmentManager(env_file=temp_env_file)
        config = manager.load_profile("pm")
        env_vars = manager.inject_env_vars(config)

        assert env_vars.get("EXISTING_VAR") == "existing-value"

        # Cleanup
        del os.environ["EXISTING_VAR"]

    def test_config_isolation_between_profiles(
        self, temp_env_file: Path, clean_env: None
    ) -> None:
        """Test that configurations are isolated between profiles."""
        manager = EnvironmentManager(env_file=temp_env_file)

        pm_config = manager.load_profile("pm")
        arch_config = manager.load_profile("arch")

        # Verify different API keys
        assert pm_config.api_key == "test-pm-key-12345"
        assert arch_config.api_key == "test-arch-key-12345"

        # Verify different config directories
        assert pm_config.config_dir != arch_config.config_dir
        assert "pm" in str(pm_config.config_dir)
        assert "arch" in str(arch_config.config_dir)

        # Verify different session IDs
        assert pm_config.session_id != arch_config.session_id

    def test_path_expansion_with_env_vars(self, tmp_path: Path) -> None:
        """Test path expansion with environment variables."""
        os.environ["TEST_CONFIG_BASE"] = str(tmp_path)

        manager = EnvironmentManager()
        expanded = manager._expand_path("$TEST_CONFIG_BASE/claude")

        assert str(tmp_path) in str(expanded)
        assert expanded.is_absolute()

        # Cleanup
        del os.environ["TEST_CONFIG_BASE"]

    def test_ensure_config_dirs_creates_all(self, tmp_path: Path) -> None:
        """Test that ensure_config_dirs creates all profile directories."""
        # Temporarily modify PROFILE_MAPPING for testing
        original_mapping = EnvironmentManager.PROFILE_MAPPING.copy()

        test_mapping = {
            "pm": {"key_var": "CLAUDE_API_KEY_PM", "config_dir": str(tmp_path / "pm")},
            "arch": {"key_var": "CLAUDE_API_KEY_ARCH", "config_dir": str(tmp_path / "arch")},
            "eng": {"key_var": "CLAUDE_API_KEY_ENG", "config_dir": str(tmp_path / "eng")},
            "qa": {"key_var": "CLAUDE_API_KEY_QA", "config_dir": str(tmp_path / "qa")},
        }

        with patch.object(EnvironmentManager, "PROFILE_MAPPING", test_mapping):
            manager = EnvironmentManager()
            dirs = manager.ensure_config_dirs()

            assert len(dirs) == 4
            for profile_name, dir_path in dirs.items():
                assert dir_path.exists()
                assert dir_path.is_dir()

    def test_get_all_profiles(self) -> None:
        """Test getting list of all profiles."""
        manager = EnvironmentManager()
        profiles = manager.get_all_profiles()

        assert "pm" in profiles
        assert "arch" in profiles
        assert "eng" in profiles
        assert "qa" in profiles
        assert len(profiles) == 4

    def test_clear_cache(self, temp_env_file: Path, clean_env: None) -> None:
        """Test clearing the configuration cache."""
        manager = EnvironmentManager(env_file=temp_env_file)

        config1 = manager.load_profile("pm")
        manager.clear_cache()
        config2 = manager.load_profile("pm")

        assert config1 is not config2  # Different object after cache clear

    def test_get_env_summary(self, temp_env_file: Path, clean_env: None) -> None:
        """Test getting environment summary."""
        manager = EnvironmentManager(env_file=temp_env_file)
        summary = manager.get_env_summary()

        assert summary["loaded"] is True
        assert "profiles" in summary
        assert "pm" in summary["profiles"]
        assert summary["profiles"]["pm"]["has_key"] is True


class TestEnvironmentConfigIntegration:
    """Integration tests for environment configuration."""

    def test_full_workflow(
        self, temp_env_file: Path, clean_env: None, tmp_path: Path
    ) -> None:
        """Test complete workflow: load, inject, use."""
        manager = EnvironmentManager(env_file=temp_env_file)

        # Load all profiles
        configs = {}
        for profile in ["pm", "arch", "eng", "qa"]:
            configs[profile] = manager.load_profile(profile)

        # Inject environment for each
        for profile, config in configs.items():
            env_vars = manager.inject_env_vars(config)

            assert env_vars["ANTHROPIC_API_KEY"] == config.api_key
            assert env_vars["CLAUDE_PROFILE"] == profile
            assert config.config_dir.exists()

    def test_multiple_managers_share_env(
        self, temp_env_file: Path, clean_env: None
    ) -> None:
        """Test that multiple managers share the same loaded environment."""
        manager1 = EnvironmentManager(env_file=temp_env_file)
        manager2 = EnvironmentManager(env_file=temp_env_file)

        config1 = manager1.load_profile("pm")
        config2 = manager2.load_profile("pm")

        assert config1.api_key == config2.api_key
