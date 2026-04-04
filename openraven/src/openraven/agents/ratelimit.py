from __future__ import annotations

import threading
import time


class RateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int = 3600) -> tuple[bool, int]:
        """Check if a request is allowed. Returns (allowed, remaining_requests)."""
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            if key not in self._requests:
                self._requests[key] = []
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            count = len(self._requests[key])
            if count >= limit:
                return False, 0
            self._requests[key].append(now)
            remaining = limit - count - 1
            return True, remaining
