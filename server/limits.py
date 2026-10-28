from __future__ import annotations

import datetime
import threading
import time
from collections import deque
from typing import Callable

from .runner import DemoError


class RateLimiter:
    """A per-visitor limit of `per_minute` runs in any 60 seconds, and a
    `daily_cap` on runs from everyone together per UTC day. Kept in memory,
    so it resets when the server restarts."""

    def __init__(self, per_minute: int, daily_cap: int, clock: Callable[[], float] = time.time) -> None:
        self._per_minute = per_minute
        self._daily_cap = daily_cap
        self._clock = clock
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = {}
        self._day: datetime.date | None = None
        self._today = 0

    def hit(self, visitor: str) -> None:
        """Counts one run, or raises a DemoError if it is over a limit."""
        with self._lock:
            now = self._clock()
            window = self._hits.setdefault(visitor, deque())
            while window and window[0] <= now - 60:
                window.popleft()
            if len(window) >= self._per_minute:
                wait = max(1, round(window[0] + 60 - now))
                raise DemoError(
                    "rate_limited",
                    f"You are asking questions a little fast. Please wait {wait} seconds and try again.",
                    429,
                )

            day = datetime.datetime.fromtimestamp(now, datetime.timezone.utc).date()
            if day != self._day:
                self._day, self._today = day, 0
            if self._today >= self._daily_cap:
                raise DemoError(
                    "demo_limit",
                    "Demo limit reached: the live demo has answered its quota of questions for today. "
                    "Please come back tomorrow, or watch the recorded demo on this page.",
                    429,
                )

            window.append(now)
            self._today += 1
            if len(self._hits) > 10_000:
                self._hits = {k: v for k, v in self._hits.items() if v and v[-1] > now - 60}

    def remaining_today(self) -> int:
        with self._lock:
            today = datetime.datetime.fromtimestamp(self._clock(), datetime.timezone.utc).date()
            used = self._today if today == self._day else 0
            return max(0, self._daily_cap - used)
