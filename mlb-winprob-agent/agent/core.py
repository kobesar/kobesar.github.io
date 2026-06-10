"""The per-tick decision pipeline, shared by live, replay, and mock modes.

One tick: update marks -> fair value -> risk heartbeat -> signal -> (risk-checked)
order -> execute -> build & log Decision. A Decision is ALWAYS produced, even
when the action is "none".
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .config import Config
from .execution.base import Executor
from .fairvalue.estimator import FairValueEstimator
from .models import BookState, Decision, GameState, Order
from .obs.logger import DecisionLogger
from .risk.gate import RiskGate
from .signal.engine import PositionView, SignalEngine


class Agent:
    def __init__(self, cfg: Config, estimator: FairValueEstimator, signal: SignalEngine,
                 executor: Executor, risk: RiskGate, logger: DecisionLogger) -> None:
        self.cfg = cfg
        self.estimator = estimator
        self.signal = signal
        self.executor = executor
        self.risk = risk
        self.logger = logger
        self._entry_ts: Optional[datetime] = None

    def _position_view(self, now: datetime) -> PositionView:
        pnl = self.executor.pnl()
        pos = self.executor.position()
        if abs(pos) < 1e-9:
            self._entry_ts = None
        return PositionView(
            shares=pos,
            avg_entry=self.executor.avg_entry,
            marked_pnl=pnl["marked"],
            entry_ts=self._entry_ts,
        )

    def _flatten(self) -> None:
        pos = self.executor.position()
        if abs(pos) < 1e-9:
            return
        side = "sell" if pos > 0 else "buy"
        self.executor.submit(Order(side=side, size=abs(pos), reason="flatten"))
        self._entry_ts = None

    def process_tick(self, gs: GameState, book: BookState, now: datetime) -> Decision:
        self.executor.update_market(book)
        fv = self.estimator.estimate(gs)

        action = "none"
        reason = ""
        edge: Optional[float] = None

        # heartbeat first -- it can halt the whole agent
        halt_reason = self.risk.heartbeat(gs, book, self.executor, now)
        if halt_reason:
            self.executor.cancel_all()
            self._flatten()
            action, reason = "halt", halt_reason
        else:
            pos = self._position_view(now)
            proposal = self.signal.evaluate(gs, book, fv, pos, now)
            edge = proposal.edge
            action, reason = proposal.action, proposal.reason

            if action in ("enter_long", "enter_short"):
                side = "buy" if action == "enter_long" else "sell"
                order = Order(side=side, size=self.cfg.signal.order_size, reason=reason)
                rr = self.risk.check_order(order, fv, gs, book, self.executor, now)
                if rr.approved:
                    order = order.model_copy(update={"size": rr.size})
                    fills = self.executor.submit(order)
                    if fills:
                        self._entry_ts = now
                        reason = f"{reason}:{rr.reason}"
                    else:
                        action, reason = "none", "no_fill"
                else:
                    action, reason = "none", f"risk_rejected:{rr.reason}"
            elif action == "exit":
                self._flatten()

        pnl = self.executor.pnl()
        decision = Decision(
            ts=now, game_state=gs, book=book, fair_value=fv, edge=edge,
            action=action, reason=reason,
            position=self.executor.position(), avg_entry=self.executor.avg_entry,
            realized_pnl=pnl["realized"], marked_pnl=pnl["marked"],
        )
        self.logger.log_decision(decision)
        self.logger.maybe_log_snapshot(book)
        self.risk.observe(fv)
        return decision
