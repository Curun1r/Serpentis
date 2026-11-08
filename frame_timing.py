"""Frame pacing in seconds, without pygame's integer-millisecond FPS rounding."""
from collections import deque
import time


class FrameLimiter:
    def __init__(self, clock=time.perf_counter, sleeper=time.sleep):
        self._clock = clock
        self._sleep = sleeper
        self._last = None
        self._cap = None
        self._samples = deque(maxlen=120)

    def tick(self, cap: int) -> float:
        if cap != self._cap:
            self._samples.clear()
            self._cap = cap
        now = self._clock()
        if self._last is None:
            self._last = now
            return 0.0
        if cap > 0:
            interval = 1.0 / cap
            deadline = self._last + interval
            remaining = deadline - now
            # Long sleeps can overshoot by several ms on macOS. Wake ahead
            # of the deadline, then use short sleeps (no CPU busy-wait).
            guard = min(.005, interval * .3)
            while remaining > 0:
                self._sleep(remaining - guard if remaining > guard else min(remaining, .0001))
                now = self._clock()
                remaining = deadline - now
        dt = max(0.0, now - self._last)
        self._last = now
        if dt > 0:
            self._samples.append(dt)
        return dt

    @property
    def fps(self) -> float:
        elapsed = sum(self._samples)
        return len(self._samples) / elapsed if elapsed > 0 else 0.0
