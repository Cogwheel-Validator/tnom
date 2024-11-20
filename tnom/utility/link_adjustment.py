"""Utility module for adjusting API links.

Usage:
    Used to adjust API links.
"""
from __future__ import annotations

from typing import AsyncGenerator


async def link_adjustment(
    apis: list[str],
) -> AsyncGenerator[str, None]:
    """Adjust API links by removing trailing slash if present."""
    for api in apis:
        if api.endswith("/"):
            checked_api = api[:-1]
        yield checked_api
