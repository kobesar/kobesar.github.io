"""Single source of time for the whole agent.

Everything that needs "now" must go through a Clock. In live mode this is just
wall-clock UTC. In replay mode the clock is driven by the timestamps of the
logged events, so age/staleness checks behave exactly as they did live.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware UTC now. Use this instead of datetime.utcnow()."""
    return datetime.now(timezone.utc)


class Clock:
    """Live clock: returns real wall-clock UTC."""

    def now(self) -> datetime:
        return utcnow()


class ReplayClock(Clock):
    """Replay clock: time advances only when the replayer sets it.

    The replayer calls ``set(ts)`` as it emits each logged record, so all
    age/staleness math downstream sees the same relative timing as the live run.
    """

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or utcnow()

    def now(self) -> datetime:
        return self._now

    def set(self, ts: datetime) -> None:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        self._now = ts
