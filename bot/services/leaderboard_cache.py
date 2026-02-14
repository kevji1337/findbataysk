"""In-memory cache for public leaderboard text."""

from dataclasses import dataclass
from time import monotonic
from typing import Optional

from bot.config import settings


@dataclass
class CacheEntry:
    version: int
    expires_at: float
    text: str


_CACHE: dict[str, CacheEntry] = {}
_VERSION: int = 0
_TTL_SECONDS: float = max(1.0, float(settings.leaderboard_cache_ttl_seconds))


def invalidate_leaderboard_cache() -> None:
    """Invalidate all leaderboard cache entries."""
    global _VERSION
    _VERSION += 1


def get_cached_leaderboard_text(period: str) -> Optional[str]:
    entry = _CACHE.get(period)
    if entry is None:
        return None
    if entry.version != _VERSION:
        return None
    if entry.expires_at < monotonic():
        return None
    return entry.text


def set_cached_leaderboard_text(period: str, text: str) -> None:
    _CACHE[period] = CacheEntry(
        version=_VERSION,
        expires_at=monotonic() + _TTL_SECONDS,
        text=text,
    )
