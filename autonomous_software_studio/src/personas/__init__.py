"""Agent system prompts and persona definitions.

This package contains the system prompts for each agent persona:
- pm_prompt.md: Product Manager persona
- architect_prompt.md: Software Architect persona
- engineer_prompt.md: Senior Engineer persona
- qa_prompt.md: QA Engineer persona

Prompts are loaded dynamically by the BaseAgent class based on profile_name.
"""

from pathlib import Path

# Directory containing persona prompts
PERSONAS_DIR = Path(__file__).parent

# Available persona profiles
PROFILES = ["pm", "arch", "eng", "qa"]


def get_prompt_path(profile_name: str) -> Path:
    """Get the path to a persona's prompt file.

    Args:
        profile_name: The profile name (pm, arch, eng, qa).

    Returns:
        Path to the prompt markdown file.

    Raises:
        ValueError: If profile name is invalid.
    """
    if profile_name not in PROFILES:
        raise ValueError(
            f"Invalid profile '{profile_name}'. "
            f"Valid profiles: {', '.join(PROFILES)}"
        )
    return PERSONAS_DIR / f"{profile_name}_prompt.md"


def load_prompt(profile_name: str) -> str:
    """Load a persona's system prompt.

    Args:
        profile_name: The profile name (pm, arch, eng, qa).

    Returns:
        The system prompt content.

    Raises:
        ValueError: If profile name is invalid.
        FileNotFoundError: If prompt file doesn't exist.
    """
    prompt_path = get_prompt_path(profile_name)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


__all__ = [
    "PERSONAS_DIR",
    "PROFILES",
    "get_prompt_path",
    "load_prompt",
]
