"""StatsAPI live-feed poller -> GameState stream.

Polls https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live every
`mlb_poll_seconds`. The JSON parser is a pure function so it can be unit-tested
without network access (important: this environment geoblocks/firewalls the
real feed -- see README section 2 findings).
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Optional

from ..clock import utcnow
from ..models import GameState

_STATUS_MAP = {
    "preview": "scheduled",
    "live": "live",
    "final": "final",
}


def _parse_source_ts(meta: dict[str, Any]) -> Optional[datetime]:
    ts = meta.get("timeStamp")
    if not ts:
        return None
    try:
        return datetime.strptime(ts, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _base_state(offense: dict[str, Any]) -> int:
    state = 0
    if offense.get("first"):
        state |= 1
    if offense.get("second"):
        state |= 2
    if offense.get("third"):
        state |= 4
    return state


def parse_feed(payload: dict[str, Any], game_pk: int, *, ingested_at: Optional[datetime] = None) -> GameState:
    """Parse a StatsAPI feed/live payload into a GameState. Pure function."""
    ingested_at = ingested_at or utcnow()
    game_data = payload.get("gameData", {})
    live = payload.get("liveData", {})
    line = live.get("linescore", {})

    status_obj = game_data.get("status", {})
    abstract = str(status_obj.get("abstractGameState", "")).lower()
    detailed = str(status_obj.get("detailedState", "")).lower()
    if "delay" in detailed or "suspend" in detailed:
        status = "delayed"
    else:
        status = _STATUS_MAP.get(abstract, "unknown")

    half_raw = str(line.get("inningHalf", "")).lower()
    half = "bottom" if half_raw.startswith("bot") else "top"

    teams = line.get("teams", {})
    home_score = int(teams.get("home", {}).get("runs", 0) or 0)
    away_score = int(teams.get("away", {}).get("runs", 0) or 0)

    return GameState(
        game_pk=game_pk,
        inning=int(line.get("currentInning", 1) or 1),
        half=half,
        outs=int(line.get("outs", 0) or 0),
        base_state=_base_state(line.get("offense", {})),
        home_score=home_score,
        away_score=away_score,
        status=status,
        source_ts=_parse_source_ts(payload.get("metaData", {})),
        ingested_at=ingested_at,
    )


def _states_differ(a: GameState, b: GameState) -> bool:
    fields = ("inning", "half", "outs", "base_state", "home_score", "away_score", "status")
    return any(getattr(a, f) != getattr(b, f) for f in fields)


class MlbFeed:
    """Background poller. Thread-safe `latest()`.

    Designed so the run loop just reads `latest()`; the poll thread keeps it
    fresh and sets `state_changed` on the emitted state when it differs from the
    previous good state.
    """

    def __init__(self, game_pk: int, base_url: str, poll_seconds: float = 3.0) -> None:
        self.game_pk = game_pk
        self.base_url = base_url.rstrip("/")
        self.poll_seconds = poll_seconds
        self._lock = threading.Lock()
        self._latest: Optional[GameState] = None
        self._fail_count = 0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        return f"{self.base_url}/api/v1.1/game/{self.game_pk}/feed/live"

    def latest(self) -> Optional[GameState]:
        with self._lock:
            return self._latest

    def _ingest(self, payload: dict[str, Any]) -> None:
        gs = parse_feed(payload, self.game_pk)
        with self._lock:
            prev = self._latest
            gs.state_changed = prev is None or _states_differ(prev, gs)
            self._latest = gs
            self._fail_count = 0

    def _on_failure(self) -> None:
        with self._lock:
            self._fail_count += 1
            if self._fail_count >= 3 and self._latest is not None:
                # keep last good state but mark it unknown after repeated failures
                self._latest = self._latest.model_copy(update={"status": "unknown"})

    def _poll_once(self, client) -> None:
        try:
            resp = client.get(self.url, timeout=10.0)
            resp.raise_for_status()
            self._ingest(resp.json())
        except Exception:  # network/parse failures both keep-last-good
            self._on_failure()

    def start(self) -> None:
        import httpx  # imported lazily so tests don't require network

        def loop() -> None:
            with httpx.Client() as client:
                while not self._stop.is_set():
                    self._poll_once(client)
                    self._stop.wait(self.poll_seconds)

        self._thread = threading.Thread(target=loop, name="mlb-feed", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
