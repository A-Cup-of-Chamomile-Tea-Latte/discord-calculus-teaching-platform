from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable, Hashable
from dataclasses import dataclass, field


@dataclass(slots=True)
class _ThrottleState:
    next_allowed_at: float = 0.0
    blocked_until: float = 0.0
    rejected_at: deque[float] = field(default_factory=deque)


class InteractionThrottle:
    """Small in-process guard that rejects rapid repeats before repository work."""

    def __init__(
        self,
        *,
        interval_seconds: float = 5.0,
        abuse_window_seconds: float = 30.0,
        abuse_threshold: int = 3,
        abuse_cooldown_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if min(interval_seconds, abuse_window_seconds, abuse_cooldown_seconds) <= 0:
            raise ValueError("Throttle intervals must be positive")
        if abuse_threshold <= 0:
            raise ValueError("abuse_threshold must be positive")
        self.interval_seconds = interval_seconds
        self.abuse_window_seconds = abuse_window_seconds
        self.abuse_threshold = abuse_threshold
        self.abuse_cooldown_seconds = abuse_cooldown_seconds
        self.clock = clock
        self._states: dict[Hashable, _ThrottleState] = {}

    def retry_after(self, key: Hashable) -> int | None:
        now = self.clock()
        state = self._states.setdefault(key, _ThrottleState())
        cutoff = now - self.abuse_window_seconds
        while state.rejected_at and state.rejected_at[0] <= cutoff:
            state.rejected_at.popleft()

        if state.blocked_until > now:
            return max(1, math.ceil(state.blocked_until - now))
        if state.next_allowed_at > now:
            state.rejected_at.append(now)
            if len(state.rejected_at) >= self.abuse_threshold:
                state.blocked_until = now + self.abuse_cooldown_seconds
                state.rejected_at.clear()
                return math.ceil(self.abuse_cooldown_seconds)
            return max(1, math.ceil(state.next_allowed_at - now))

        state.next_allowed_at = now + self.interval_seconds
        if len(self._states) > 1_024:
            self._discard_idle_states(now)
        return None

    def _discard_idle_states(self, now: float) -> None:
        idle_before = now - self.abuse_window_seconds
        self._states = {
            key: state
            for key, state in self._states.items()
            if state.blocked_until > now
            or state.next_allowed_at > idle_before
            or bool(state.rejected_at)
        }
