"""Agent account and usage settings management."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


PROVIDERS = [
    "anthropic",
    "claude_code",
    "groq",
    "openai",
    "azure_openai",
    "custom",
]


class UsageLimitError(Exception):
    """Raised when an agent exceeds the configured usage limit."""

    pass


@dataclass
class PromptVersion:
    """Prompt version metadata."""

    path: str
    created_at: str
    note: str = ""


class AgentSettingsManager:
    """Manage agent account settings stored in JSON."""

    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = settings_path or Path("data/agent_settings.json")
        self.history_dir = self.settings_path.parent / "agent_settings.history"
        self.prompts_dir = self.settings_path.parent / "prompts"
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings = self._load_or_init()

    def _default_agent(self, profile: str) -> dict[str, Any]:
        return {
            "profile": profile,
            "provider": "anthropic",
            "model": "",
            "auth_type": "api_key",  # api_key | token | none
            "api_key": "",
            "auth_token": "",
            "auth_env_var": "CLAUDE_CODE_TOKEN",
            "env_overrides": {},
            "daily_limit": 0,
            "usage_today": 0,
            "usage_reset_at": date.today().isoformat(),
            "hard_limit": False,
            "usage_unit": "runs",
            "account_label": "",
            "claude_profile_dir": "",
            "prompt_active_path": "",
            "prompt_history": [],
        }

    def _default_settings(self) -> dict[str, Any]:
        return {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "agents": {
                "pm": self._default_agent("pm"),
                "arch": self._default_agent("arch"),
                "eng": self._default_agent("eng"),
                "qa": self._default_agent("qa"),
            },
        }

    def _load_or_init(self) -> dict[str, Any]:
        if self.settings_path.exists():
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
        else:
            data = self._default_settings()
            self._write_settings(data)
            return data

        # Ensure required structure
        if "agents" not in data or not isinstance(data["agents"], dict):
            data = self._default_settings()
            self._write_settings(data)
            return data

        for profile in ["pm", "arch", "eng", "qa"]:
            if profile not in data["agents"]:
                data["agents"][profile] = self._default_agent(profile)
            else:
                # Fill in missing keys
                defaults = self._default_agent(profile)
                for key, value in defaults.items():
                    data["agents"][profile].setdefault(key, deepcopy(value))

        return data

    def _write_settings(self, data: dict[str, Any]) -> None:
        self.history_dir.mkdir(parents=True, exist_ok=True)
        if self.settings_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.history_dir / f"agent_settings_{timestamp}.json"
            shutil.copy2(self.settings_path, backup_path)

        data["updated_at"] = datetime.now().isoformat()
        self.settings_path.write_text(
            json.dumps(data, indent=2, sort_keys=False),
            encoding="utf-8",
        )

    def reload(self) -> None:
        self._settings = self._load_or_init()

    def get_settings(self) -> dict[str, Any]:
        return deepcopy(self._settings)

    def get_agent(self, profile: str) -> dict[str, Any]:
        profile = profile.lower()
        agent = self._settings["agents"].get(profile, self._default_agent(profile))
        return deepcopy(agent)

    def update_agent(self, profile: str, updates: dict[str, Any]) -> dict[str, Any]:
        profile = profile.lower()
        agent = self._settings["agents"].get(profile, self._default_agent(profile))
        agent.update(deepcopy(updates))
        self._settings["agents"][profile] = agent
        self._write_settings(self._settings)
        return deepcopy(agent)

    def reset_usage(self, profile: str) -> dict[str, Any]:
        profile = profile.lower()
        agent = self._settings["agents"].get(profile, self._default_agent(profile))
        agent["usage_today"] = 0
        agent["usage_reset_at"] = date.today().isoformat()
        self._settings["agents"][profile] = agent
        self._write_settings(self._settings)
        return deepcopy(agent)

    def _refresh_usage(self, agent: dict[str, Any]) -> dict[str, Any]:
        reset_at = agent.get("usage_reset_at") or date.today().isoformat()
        today = date.today().isoformat()
        if reset_at != today:
            agent["usage_today"] = 0
            agent["usage_reset_at"] = today
        return agent

    def check_and_record_usage(self, profile: str, units: int = 1) -> str | None:
        profile = profile.lower()
        agent = self._settings["agents"].get(profile, self._default_agent(profile))
        agent = self._refresh_usage(agent)

        limit = int(agent.get("daily_limit") or 0)
        usage = int(agent.get("usage_today") or 0)
        hard_limit = bool(agent.get("hard_limit"))

        warning: str | None = None
        if limit > 0 and usage + units > limit:
            message = (
                f"{profile} usage limit exceeded ({usage}/{limit} {agent.get('usage_unit', 'runs')})."
            )
            if hard_limit:
                raise UsageLimitError(message)
            warning = message

        agent["usage_today"] = usage + units
        self._settings["agents"][profile] = agent
        self._write_settings(self._settings)
        return warning

    def get_prompt_path(self, profile: str) -> Path:
        profile = profile.lower()
        agent = self._settings["agents"].get(profile, self._default_agent(profile))
        active_path = agent.get("prompt_active_path")
        if active_path and Path(active_path).exists():
            return Path(active_path)

        return Path("src") / "personas" / f"{profile}_prompt.md"

    def read_prompt(self, profile: str) -> str:
        path = self.get_prompt_path(profile)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _append_prompt_history(
        self, profile: str, path: Path, note: str = ""
    ) -> None:
        agent = self._settings["agents"].get(profile, self._default_agent(profile))
        history = list(agent.get("prompt_history", []))
        history.append(
            {
                "path": str(path),
                "created_at": datetime.now().isoformat(),
                "note": note,
            }
        )
        agent["prompt_history"] = history
        self._settings["agents"][profile] = agent

    def save_prompt_version(
        self, profile: str, content: str, note: str = ""
    ) -> Path:
        profile = profile.lower()
        agent_dir = self.prompts_dir / profile
        agent_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_path = agent_dir / f"{profile}_prompt_{timestamp}.md"
        version_path.write_text(content, encoding="utf-8")

        agent = self._settings["agents"].get(profile, self._default_agent(profile))
        agent["prompt_active_path"] = str(version_path)
        self._settings["agents"][profile] = agent
        self._append_prompt_history(profile, version_path, note)
        self._write_settings(self._settings)
        return version_path

    def list_prompt_versions(self, profile: str) -> list[PromptVersion]:
        profile = profile.lower()
        agent = self._settings["agents"].get(profile, self._default_agent(profile))
        history = agent.get("prompt_history", [])
        versions: list[PromptVersion] = []
        for entry in history:
            versions.append(
                PromptVersion(
                    path=entry.get("path", ""),
                    created_at=entry.get("created_at", ""),
                    note=entry.get("note", ""),
                )
            )
        return versions

    def set_active_prompt(self, profile: str, path: Path) -> None:
        profile = profile.lower()
        agent = self._settings["agents"].get(profile, self._default_agent(profile))
        agent["prompt_active_path"] = str(path)
        self._settings["agents"][profile] = agent
        self._write_settings(self._settings)

    def use_default_prompt(self, profile: str) -> None:
        profile = profile.lower()
        agent = self._settings["agents"].get(profile, self._default_agent(profile))
        agent["prompt_active_path"] = ""
        self._settings["agents"][profile] = agent
        self._write_settings(self._settings)

    def apply_env_overrides(self, profile: str, env_vars: dict[str, str]) -> dict[str, str]:
        profile = profile.lower()
        agent = self._settings["agents"].get(profile, self._default_agent(profile))
        env_vars = dict(env_vars)

        provider = agent.get("provider") or "anthropic"
        model = agent.get("model") or ""
        api_key = agent.get("api_key") or ""
        auth_type = agent.get("auth_type") or "api_key"
        auth_token = agent.get("auth_token") or ""
        auth_env_var = agent.get("auth_env_var") or "CLAUDE_CODE_TOKEN"

        if model and provider in {"anthropic", "claude_code"}:
            env_vars["CLAUDE_MODEL"] = model

        if auth_type == "api_key" and api_key:
            if provider == "anthropic":
                env_vars["ANTHROPIC_API_KEY"] = api_key
            elif provider == "openai":
                env_vars["OPENAI_API_KEY"] = api_key
            elif provider == "azure_openai":
                env_vars["AZURE_OPENAI_API_KEY"] = api_key
            elif provider == "groq":
                env_vars["GROQ_API_KEY"] = api_key
            else:
                env_vars["API_KEY"] = api_key

        if auth_type == "token" and auth_token:
            env_vars[auth_env_var] = auth_token

        for key, value in (agent.get("env_overrides") or {}).items():
            if key:
                env_vars[str(key)] = str(value)

        return env_vars
