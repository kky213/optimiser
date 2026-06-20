"""User config loader for Optimiser (~/.optimiser/config.yaml)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_USER_CONFIG_PATH = Path.home() / ".optimiser" / "config.yaml"
_DEFAULT_CONFIG: dict[str, Any] = {
    "proxy": {
        "port": 8787,
        "host": "127.0.0.1",
        "mode": "token",
    },
    "compression": {
        "output_shaping": True,
        "effort_routing": True,
        "code_aware": True,
        "interceptors": True,
        "tool_profiles": True,
    },
    "memory": {
        "enabled": True,
        "storage": "project",
        "top_k": 10,
        "async_lookup": True,
        "ccr_learning": True,
    },
    "dashboard": {
        "enabled": True,
        "refresh_hz": 2,
        "show_cost_estimate": True,
        "currency": "USD",
        "price_per_mtok_input": 3.0,
    },
    "telemetry": {
        "enabled": False,
    },
}

_LOADED: dict[str, Any] | None = None


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_user_config() -> dict[str, Any]:
    global _LOADED
    if _LOADED is not None:
        return _LOADED

    config = dict(_DEFAULT_CONFIG)

    if _USER_CONFIG_PATH.exists():
        try:
            import yaml  # type: ignore[import]
            with open(_USER_CONFIG_PATH, encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}
            config = _deep_merge(config, user_cfg)
        except Exception:
            pass

    # Apply env var overrides on top
    if os.environ.get("OPTIMISER_MEMORY", "").lower() in ("0", "false", "no"):
        config.setdefault("memory", {})["enabled"] = False
    if os.environ.get("HEADROOM_OUTPUT_SHAPER", "").lower() in ("0", "false", "no"):
        config.setdefault("compression", {})["output_shaping"] = False
    if os.environ.get("OPTIMISER_CODE_AWARE_ENABLED", "").lower() in ("0", "false", "no"):
        config.setdefault("compression", {})["code_aware"] = False
    if os.environ.get("HEADROOM_TELEMETRY", "").lower() in ("off", "0", "false"):
        config.setdefault("telemetry", {})["enabled"] = False

    _LOADED = config
    return config


def get(section: str, key: str, default: Any = None) -> Any:
    """Convenience accessor: get a single config value."""
    cfg = load_user_config()
    return cfg.get(section, {}).get(key, default)


def write_default_config() -> Path:
    """Write the default config to ~/.optimiser/config.yaml if it doesn't exist."""
    _USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _USER_CONFIG_PATH.exists():
        content = """# Optimiser User Configuration
# Edit this file to customise behaviour.
# Full docs: optimiser --help

proxy:
  port: 8787
  host: 127.0.0.1
  mode: token                    # token | cache

compression:
  output_shaping: true           # reduce model output verbosity (saves 15-25%)
  effort_routing: true           # lower effort on mechanical turns
  code_aware: true               # AST-based code compression (saves 30-70%)
  interceptors: true             # tool result pre-processing
  tool_profiles: true            # per-tool compression profiles

memory:
  enabled: true                  # persistent cross-session memory
  storage: project               # project | user | global
  top_k: 10                      # memories to inject per request
  async_lookup: true             # parallel with compression (faster)
  ccr_learning: true             # learn from CCR retrievals

dashboard:
  enabled: true
  refresh_hz: 2
  show_cost_estimate: true
  currency: USD
  price_per_mtok_input: 3.0      # adjust for your model pricing

telemetry:
  enabled: false                 # Optimiser sends no telemetry by default
"""
        _USER_CONFIG_PATH.write_text(content, encoding="utf-8")
    return _USER_CONFIG_PATH
