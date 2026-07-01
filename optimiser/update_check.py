"""Update checker — disabled in Optimiser (local-only build)."""

from __future__ import annotations

PACKAGE_NAME = "optimiser-ai"


def is_update_check_enabled() -> bool:
    return False


def installed_version() -> str | None:
    try:
        from optimiser._version import __version__
        return __version__
    except Exception:
        return None


def maybe_check_async():
    return None


def format_update_notice() -> str | None:
    return None


def run_check(**kwargs) -> str | None:
    return None


def should_check(**kwargs) -> bool:
    return False


def fetch_latest_version(**kwargs) -> str | None:
    return None


def read_cache():
    return None


def write_cache(*args, **kwargs) -> None:
    pass


__all__ = [
    "PACKAGE_NAME",
    "fetch_latest_version",
    "format_update_notice",
    "installed_version",
    "is_update_check_enabled",
    "maybe_check_async",
    "read_cache",
    "run_check",
    "should_check",
    "write_cache",
]
