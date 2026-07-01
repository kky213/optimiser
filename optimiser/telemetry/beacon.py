"""Telemetry beacon — disabled in Optimiser (local-only build)."""

from __future__ import annotations


def is_telemetry_enabled() -> bool:
    return False


def is_telemetry_warn_enabled() -> bool:
    return False


def format_telemetry_notice(*, prefix: str = "") -> str:
    return ""


class TelemetryBeacon:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass
