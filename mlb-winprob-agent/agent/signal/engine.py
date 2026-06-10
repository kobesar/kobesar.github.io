"""Signal engine: FairValue + BookState + Position -> proposed action.

Per-market state machine: FLAT -> LONG | SHORT -> FLAT.
Hysteresis is mandatory (entry_threshold > exit_threshold, enforced at config
load). Refusing to trade on stale data is a success criterion, so every refusal
path returns a clear reason string.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..config import SignalCfg
from ..models import Action, BookState, FairValue, GameState


@dataclass
class PositionView:
    shares: float = 0.0            # signed: >0 long home, <0 short home
    avg_entry: Optional[float] = None
    marked_pnl: float = 0.0        # current marked PnL (USD) on open position
    entry_ts: Optional[datetime] = None

    @property
    def is_flat(self) -> bool:
        return abs(self.shares) < 1e-9

    @property
    def is_long(self) -> bool:
        return self.shares > 1e-9

    def age_seconds(self, now: datetime) -> Optional[float]:
        if self.entry_ts is None:
            return None
        return (now - self.entry_ts).total_seconds()


@dataclass
class Proposal:
    action: Action
    reason: str
    edge: Optional[float] = None


class SignalEngine:
    def __init__(self, cfg: SignalCfg) -> None:
        self.cfg = cfg
        self._last_change_ts: Optional[datetime] = None

    def _seconds_since_change(self, gs: GameState, now: datetime) -> Optional[float]:
        if gs.state_changed:
            self._last_change_ts = now
        if self._last_change_ts is None:
            return None
        return (now - self._last_change_ts).total_seconds()

    def evaluate(self, gs: GameState, book: BookState, fv: Optional[FairValue],
                 pos: PositionView, now: datetime) -> Proposal:
        c = self.cfg
        since_change = self._seconds_since_change(gs, now)

        # need a fair value and a usable mid to do anything
        if fv is None:
            return Proposal("none", "no_fair_value")
        mid = book.mid
        if mid is None:
            return Proposal("none", "no_market_price")
        edge = fv.prob - mid

        # ----- exits take priority when in a position -----
        if not pos.is_flat:
            if abs(edge) < c.exit_threshold:
                return Proposal("exit", "edge_reverted", edge)
            if pos.marked_pnl <= -c.per_position_stop:
                return Proposal("exit", "stop_loss", edge)
            age = pos.age_seconds(now)
            if age is not None and age > c.max_hold_seconds:
                return Proposal("exit", "max_hold", edge)
            if gs.inning >= c.no_trade_from_inning:
                return Proposal("exit", "late_inning_flatten", edge)
            return Proposal("none", "holding", edge)

        # ----- entry checks (flat) -----
        if gs.status != "live":
            return Proposal("none", "game_not_live", edge)
        if book.is_stale(now):
            return Proposal("none", "stale_book", edge)
        if gs.state_age_seconds(now) >= c.max_state_age:
            return Proposal("none", "stale_game_state", edge)
        if gs.inning >= c.no_trade_from_inning:
            return Proposal("none", "no_trade_inning", edge)
        if since_change is not None and since_change < c.post_change_cooldown:
            return Proposal("none", "post_change_cooldown", edge)
        spread = book.spread
        if spread is None or spread > c.max_spread:
            return Proposal("none", "spread_too_wide", edge)
        if abs(edge) <= c.entry_threshold:
            return Proposal("none", "edge_below_threshold", edge)

        side = "ask" if edge > 0 else "bid"
        depth = book.depth_within(mid, c.depth_band_cents, side)
        if depth < c.min_depth:
            return Proposal("none", "insufficient_depth", edge)

        if edge > 0:
            return Proposal("enter_long", "edge_long", edge)
        return Proposal("enter_short", "edge_short", edge)
