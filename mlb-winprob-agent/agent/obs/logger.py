"""JSONL logging.

One JSON line per decision tick (action == "none" ticks included -- they are
the tuning dataset). Raw book snapshots go to a separate file at a configurable
cadence for replay.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from ..clock import utcnow
from ..models import BookState, Decision


def _default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError(f"not JSON serializable: {type(o)}")


class DecisionLogger:
    def __init__(self, game_pk: int, market_id: str, log_dir: str | Path = "logs",
                 snapshot_every_seconds: float = 30.0) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        day = date.today().isoformat()
        safe_market = str(market_id).replace("/", "_")
        self.decision_path = self.log_dir / f"{day}_{game_pk}_{safe_market}.jsonl"
        self.snapshot_path = self.log_dir / f"{day}_{game_pk}_{safe_market}.books.jsonl"
        self.snapshot_every_seconds = snapshot_every_seconds
        self._last_snapshot: Optional[datetime] = None
        self._dfh = self.decision_path.open("a")
        self._sfh = self.snapshot_path.open("a")

    def log_decision(self, decision: Decision) -> None:
        self._dfh.write(json.dumps(decision.model_dump(mode="json"), default=_default) + "\n")
        self._dfh.flush()

    def maybe_log_snapshot(self, book: BookState) -> None:
        now = utcnow()
        if (self._last_snapshot is None
                or (now - self._last_snapshot).total_seconds() >= self.snapshot_every_seconds):
            self._sfh.write(json.dumps(book.model_dump(mode="json"), default=_default) + "\n")
            self._sfh.flush()
            self._last_snapshot = now

    def close(self) -> None:
        for fh in (self._dfh, self._sfh):
            try:
                fh.close()
            except Exception:
                pass
