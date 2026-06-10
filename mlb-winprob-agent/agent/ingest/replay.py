"""Replay a logged JSONL session as if live.

Reads a decision log (each line embeds the GameState and BookState for that
tick) and yields them in order, advancing a ReplayClock to each tick's
timestamp so all age/staleness math behaves exactly as it did live. This is how
the whole stack is tested without a live game -- build and use it EARLY.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from ..clock import ReplayClock
from ..models import BookState, GameState


class ReplayTick:
    __slots__ = ("ts", "game_state", "book")

    def __init__(self, ts: datetime, game_state: GameState, book: BookState) -> None:
        self.ts = ts
        self.game_state = game_state
        self.book = book


def _coerce_book(raw: dict) -> BookState:
    # JSON object keys are strings; BookState wants float price keys.
    for k in ("bid_depth", "ask_depth"):
        if isinstance(raw.get(k), dict):
            raw[k] = {float(px): float(sz) for px, sz in raw[k].items()}
    return BookState.model_validate(raw)


def read_session(path: str | Path) -> list[ReplayTick]:
    ticks: list[ReplayTick] = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        gs = GameState.model_validate(rec["game_state"])
        book = _coerce_book(rec["book"])
        ts = datetime.fromisoformat(rec["ts"])
        ticks.append(ReplayTick(ts, gs, book))
    return ticks


def replay(path: str | Path, speed: float = 1.0,
           clock: Optional[ReplayClock] = None) -> Iterator[ReplayTick]:
    """Yield ticks in order. `speed` accelerates wall-clock pacing (10 = 10x).
    speed <= 0 means as-fast-as-possible. The provided ReplayClock is advanced
    to each tick's timestamp before it is yielded."""
    ticks = read_session(path)
    prev_ts: Optional[datetime] = None
    for tick in ticks:
        if clock is not None:
            clock.set(tick.ts)
        if speed and speed > 0 and prev_ts is not None:
            dt = (tick.ts - prev_ts).total_seconds() / speed
            if dt > 0:
                time.sleep(min(dt, 5.0))  # cap so a long gap doesn't hang replay
        prev_ts = tick.ts
        yield tick
