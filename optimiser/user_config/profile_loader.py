"""Per-tool compression profile loader for Optimiser."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_DEFAULT_PROFILES_PATH = Path(__file__).parent / "tool_profiles.yaml"
_USER_PROFILES_PATH = Path.home() / ".optimiser" / "tool_profiles.yaml"

_LOADED: dict[str, Any] | None = None


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import]
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # PyYAML not available — return empty (graceful degradation)
        return {}
    except FileNotFoundError:
        return {}


def load_profiles() -> dict[str, Any]:
    global _LOADED
    if _LOADED is not None:
        return _LOADED

    profiles: dict[str, Any] = {}

    default_data = _load_yaml(_DEFAULT_PROFILES_PATH)
    profiles.update(default_data.get("profiles", {}))

    # User overrides merge on top
    if _USER_PROFILES_PATH.exists():
        user_data = _load_yaml(_USER_PROFILES_PATH)
        profiles.update(user_data.get("profiles", {}))

    _LOADED = profiles
    return profiles


def match_profile(
    tool_name: str | None,
    content: str,
    token_count: int,
) -> dict[str, Any] | None:
    """Return the first matching profile for this tool call, or None."""
    profiles = load_profiles()

    content_lower = (content or "")[:200].lower()

    for _name, profile in profiles.items():
        min_tokens = profile.get("min_tokens", 0)
        if token_count < min_tokens:
            continue

        for trigger in profile.get("triggers", []):
            if not isinstance(trigger, dict):
                continue

            # token count gates
            if "token_count_lt" in trigger and token_count >= trigger["token_count_lt"]:
                continue
            if "token_count_lt" in trigger and token_count < trigger["token_count_lt"]:
                return profile

            # tool name match
            if "tool_name" in trigger and tool_name:
                if trigger["tool_name"].lower() == tool_name.lower():
                    return profile

            # content type (rough heuristic)
            if "content_type" in trigger:
                ct = trigger["content_type"].lower()
                if ct == "json" and (content_lower.startswith("{") or content_lower.startswith("[")):
                    return profile
                if ct == "html" and ("<html" in content_lower or "<!doctype" in content_lower):
                    return profile

            # content prefix match
            if "content_starts_with" in trigger:
                if (content or "").startswith(trigger["content_starts_with"]):
                    return profile

    return None


def get_strategy_for_tool(
    tool_name: str | None,
    content: str,
    token_count: int,
) -> str | None:
    """Return the compression strategy name for this tool call, or None for auto."""
    profile = match_profile(tool_name, content, token_count)
    if profile is None:
        return None
    return profile.get("strategy")
