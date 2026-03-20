"""
Optional in-memory passport cache.

Useful for scripts that connect to TM1 multiple times — avoids repeated
browser logins within the same Python process. Not used automatically;
opt in by using PassportCache explicitly.
"""

import time
from typing import Dict, Optional, Tuple


class PassportCache:
    """
    Simple in-memory cache keyed by auth_url.

    Passports have no guaranteed expiry time exposed by TM1, so cache entries
    are evicted after ttl_seconds (default 1 hour). If a cached passport is
    rejected by TM1py, catch the exception and call invalidate() then
    get_cam_passport() again.

    Example:
        >>> from tm1_auth import get_cam_passport
        >>> from tm1_auth.cache import PassportCache
        >>>
        >>> cache = PassportCache(ttl_seconds=3600)
        >>>
        >>> def connect(auth_url, tm1_address, port):
        ...     passport = cache.get(auth_url)
        ...     if not passport:
        ...         passport = get_cam_passport(auth_url)
        ...         cache.set(auth_url, passport)
        ...     return TM1Service(address=tm1_address, port=port,
        ...                       cam_passport=passport, ssl=True)
    """

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, Tuple[str, float]] = {}  # url -> (passport, timestamp)

    def get(self, auth_url: str) -> Optional[str]:
        """Return cached passport if present and not expired, else None."""
        entry = self._store.get(auth_url)
        if not entry:
            return None
        passport, timestamp = entry
        if time.time() - timestamp > self.ttl_seconds:
            del self._store[auth_url]
            return None
        return passport

    def set(self, auth_url: str, passport: str) -> None:
        """Store a passport for the given auth_url."""
        self._store[auth_url] = (passport, time.time())

    def invalidate(self, auth_url: str) -> None:
        """Remove a cached passport, e.g. after TM1py reports it expired."""
        self._store.pop(auth_url, None)

    def clear(self) -> None:
        """Clear all cached passports."""
        self._store.clear()
