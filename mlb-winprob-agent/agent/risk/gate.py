"""Risk gate -- final authority over trading.

The signal engine proposes; the gate approves, sizes down, or rejects, and on a
heartbeat failure it halts the whole agent (cancel all + flatten). Every
rejection is returned with a reason so it can be logged.

Pre-trade checks run before every order. Heartbeat checks run every loop tick.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import RiskCfg
from ..execution.base import Executor
from ..models import BookState, FairValue, GameState, Order


@dataclass
class RiskResult:
    approved: bool
    size: float
    reason: str


class RiskGate:
    def __init__(self, cfg: RiskCfg, book_staleness: float, state_staleness: float) -> None:
        self.cfg = cfg
        self.book_staleness = book_staleness
        self.state_staleness = state_staleness
        self.halted = False
        self.halt_reason = ""
        self._order_ts: deque[datetime] = deque()
        self._prev_fv: Optional[float] = None
        self._disagreement_since: Optional[datetime] = None

    # ----- per-tick bookkeeping -----
    def observe(self, fv: Optional[FairValue]) -> None:
        """Record this tick's fair value so the next tick can detect jumps."""
        if fv is not None:
            self._prev_fv = fv.prob

    def _loss(self, executor: Executor) -> float:
        return max(0.0, -executor.pnl()["total"])

    # ----- heartbeat: returns halt reason if the agent must stop -----
    def heartbeat(self, gs: Optional[GameState], book: Optional[BookState],
                  executor: Executor, now: datetime) -> Optional[str]:
        if Path(self.cfg.kill_file).exists():
            return self._halt("kill_switch_file")

        # feed disagreement: book live but game final (or vice versa) for > N s
        disagree = False
        if gs is not None and book is not None:
            book_live = not book.is_stale(now)
            if gs.status == "final" and book_live:
                disagree = True
            if gs.status == "live" and book.best_bid is None and book.best_ask is None:
                disagree = True
        if disagree:
            if self._disagreement_since is None:
                self._disagreement_since = now
            elif (now - self._disagreement_since).total_seconds() > self.cfg.feed_disagreement_seconds:
                return self._halt("feed_disagreement")
        else:
            self._disagreement_since = None

        # either feed stale beyond 3x its limit
        if book is not None and book.age_seconds(now) > 3 * self.book_staleness:
            return self._halt("book_feed_dead")
        if gs is not None and gs.state_age_seconds(now) > 3 * self.state_staleness:
            return self._halt("game_feed_dead")

        # loss limits also force a halt
        loss = self._loss(executor)
        if loss > self.cfg.per_game_loss_limit:
            return self._halt("per_game_loss_limit")
        if loss > self.cfg.daily_loss_limit:
            return self._halt("daily_loss_limit")
        return None

    def _halt(self, reason: str) -> str:
        self.halted = True
        self.halt_reason = reason
        return reason

    # ----- pre-trade approval -----
    def check_order(self, order: Order, fv: Optional[FairValue], gs: GameState,
                    book: BookState, executor: Executor, now: datetime) -> RiskResult:
        if self.halted:
            return RiskResult(False, 0.0, "halted")

        if fv is None:
            return RiskResult(False, 0.0, "no_fair_value")
        if not (self.cfg_fv_low <= fv.prob <= self.cfg_fv_high):
            return RiskResult(False, 0.0, "fv_out_of_bounds")

        # fv jump without a state change signals a bug -> refuse
        if (self._prev_fv is not None and not gs.state_changed
                and abs(fv.prob - self._prev_fv) > self.cfg.max_fv_jump):
            return RiskResult(False, 0.0, "fv_jump_no_state_change")

        # order rate limit
        cutoff = now.timestamp() - 60.0
        while self._order_ts and self._order_ts[0].timestamp() < cutoff:
            self._order_ts.popleft()
        if len(self._order_ts) >= self.cfg.max_orders_per_minute:
            return RiskResult(False, 0.0, "order_rate_limit")

        # loss limits
        loss = self._loss(executor)
        if loss > self.cfg.per_game_loss_limit:
            return RiskResult(False, 0.0, "per_game_loss_limit")
        if loss > self.cfg.daily_loss_limit:
            return RiskResult(False, 0.0, "daily_loss_limit")

        # position / capital limits -- size down rather than reject if possible
        price = order.limit_price or book.mid or 0.5
        signed = order.size if order.side == "buy" else -order.size
        cur = executor.position()
        resulting = cur + signed
        size = order.size

        # share cap
        if abs(resulting) > self.cfg.max_position_shares:
            allowed = self.cfg.max_position_shares - abs(cur)
            size = max(0.0, min(size, allowed))
        # usd position cap
        if abs(resulting) * price > self.cfg.max_position_usd:
            allowed_usd = self.cfg.max_position_usd - abs(cur) * price
            size = max(0.0, min(size, allowed_usd / price if price > 0 else 0.0))
        # total deployed cap
        deployed = abs(cur) * price
        if deployed + size * price > self.cfg.max_total_usd:
            allowed_usd = self.cfg.max_total_usd - deployed
            size = max(0.0, min(size, allowed_usd / price if price > 0 else 0.0))

        if size < 1e-6:
            return RiskResult(False, 0.0, "limit_blocks_order")

        self._order_ts.append(now)
        reason = "approved" if abs(size - order.size) < 1e-6 else "approved_sized_down"
        return RiskResult(True, size, reason)

    # fv bounds mirror the fairvalue clamp; kept simple as constants here
    cfg_fv_low = 0.02
    cfg_fv_high = 0.98
