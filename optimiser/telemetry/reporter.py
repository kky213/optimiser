"""Usage reporter — disabled in Optimiser (local-only build)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class LicenseInfo:
    status: str = "active"
    org_id: str | None = None
    org_name: str | None = None
    plan: str | None = None
    quota_tokens: int | None = None
    trial_expires_at: datetime | None = None
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LicenseInfo":
        return cls(status=data.get("status", "active"))


class UsageReporter:
    def __init__(self, *args, **kwargs) -> None:
        self._license_info = LicenseInfo(status="active")

    async def validate_license(self) -> LicenseInfo:
        return self._license_info

    async def start(self, proxy: Any) -> None:
        pass

    async def stop(self) -> None:
        pass

    @property
    def is_active(self) -> bool:
        return True

    @property
    def should_compress(self) -> bool:
        return True
