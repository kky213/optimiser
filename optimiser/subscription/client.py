"""Subscription client — disabled in local-only build.

No calls are made to api.anthropic.com. All methods are no-ops.
"""

from __future__ import annotations


def read_cached_oauth_token() -> str | None:
    return None


class SubscriptionClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def fetch(self, token: str | None = None):
        return None
