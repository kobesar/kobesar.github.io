"""Paper executor: conservative by construction.

- Market-style orders walk the visible book level by level from the best price;
  size beyond visible depth is rejected (no fills out of thin air).
- Every fill takes `extra_slippage_cents` adversely and a taker fee.
- Maker mode (default off): a resting order fills only if a later book update
  crosses its limit.
- Tracks signed position, avg_entry, realized_pnl, and marked_pnl (marked at
  current mid, falling back to last fill price).
"""
from __future__ import annotations

from typing import Optional

from ..clock import utcnow
from ..config import ExecutionCfg
from ..models import BookState, Fill, Order
from .base import Executor


class PaperExecutor(Executor):
    def __init__(self, cfg: ExecutionCfg) -> None:
        self.cfg = cfg
        self._pos: float = 0.0
        self._avg_entry: Optional[float] = None
        self._realized: float = 0.0
        self._book: Optional[BookState] = None
        self._last_fill_price: Optional[float] = None
        self._resting: list[Order] = []  # maker mode

    # ----- interface -----
    def update_market(self, book: BookState) -> None:
        self._book = book
        if self.cfg.maker_mode:
            self._try_resting_fills(book)

    def position(self) -> float:
        return self._pos

    @property
    def avg_entry(self) -> Optional[float]:
        return self._avg_entry

    def cancel_all(self) -> None:
        self._resting.clear()

    def _mark_price(self) -> Optional[float]:
        if self._book is not None and self._book.mid is not None:
            return self._book.mid
        return self._last_fill_price

    def pnl(self) -> dict:
        marked = 0.0
        mp = self._mark_price()
        if mp is not None and not self._is_flat and self._avg_entry is not None:
            marked = (mp - self._avg_entry) * self._pos  # signed position handles long/short
        return {"realized": round(self._realized, 6),
                "marked": round(marked, 6),
                "total": round(self._realized + marked, 6)}

    @property
    def _is_flat(self) -> bool:
        return abs(self._pos) < 1e-9

    def submit(self, order: Order) -> list[Fill]:
        if self.cfg.maker_mode and order.limit_price is not None:
            self._resting.append(order)
            return []
        if self._book is None:
            return []
        fills = self._walk_book(order, self._book)
        for f in fills:
            self._apply_fill(f)
        return fills

    # ----- fill mechanics -----
    def _walk_book(self, order: Order, book: BookState) -> list[Fill]:
        slip = self.cfg.extra_slippage_cents
        remaining = order.size
        fills: list[Fill] = []
        if order.side == "buy":
            levels = sorted(book.ask_depth.items(), key=lambda x: x[0])       # low ask first
        else:
            levels = sorted(book.bid_depth.items(), key=lambda x: x[0], reverse=True)  # high bid first
        for px, size in levels:
            if remaining <= 1e-9:
                break
            take = min(remaining, size)
            if take <= 1e-9:
                continue
            fill_px = px + slip if order.side == "buy" else px - slip
            fill_px = min(1.0, max(0.0, fill_px))
            fee = self.cfg.taker_fee * fill_px * take
            fills.append(Fill(side=order.side, size=take, price=fill_px, fee=fee, ts=utcnow()))
            remaining -= take
        # remaining beyond visible depth is simply rejected (not filled)
        return fills

    def _apply_fill(self, fill: Fill) -> None:
        signed = fill.size if fill.side == "buy" else -fill.size
        prev_pos = self._pos
        new_pos = prev_pos + signed
        self._last_fill_price = fill.price

        # realize PnL on any portion that reduces/closes the existing position
        if prev_pos != 0 and (prev_pos > 0) != (signed > 0):
            closing = min(abs(signed), abs(prev_pos))
            direction = 1.0 if prev_pos > 0 else -1.0
            if self._avg_entry is not None:
                self._realized += (fill.price - self._avg_entry) * closing * direction
            # if we flipped through zero, the remainder opens a new position
            if abs(signed) > abs(prev_pos):
                self._avg_entry = fill.price
            elif abs(new_pos) < 1e-9:
                self._avg_entry = None
        else:
            # increasing position (or opening): update average cost
            if self._is_flat_value(prev_pos) or self._avg_entry is None:
                self._avg_entry = fill.price
            else:
                total = abs(prev_pos) + abs(signed)
                self._avg_entry = (self._avg_entry * abs(prev_pos) + fill.price * abs(signed)) / total

        self._pos = new_pos
        self._realized -= fill.fee
        if abs(self._pos) < 1e-9:
            self._pos = 0.0
            self._avg_entry = None

    @staticmethod
    def _is_flat_value(p: float) -> bool:
        return abs(p) < 1e-9

    # ----- maker mode -----
    def _try_resting_fills(self, book: BookState) -> None:
        still: list[Order] = []
        for order in self._resting:
            crossed = (
                (order.side == "buy" and book.best_ask is not None and book.best_ask <= order.limit_price)
                or (order.side == "sell" and book.best_bid is not None and book.best_bid >= order.limit_price)
            )
            if crossed:
                fee = self.cfg.taker_fee * order.limit_price * order.size
                self._apply_fill(Fill(side=order.side, size=order.size,
                                      price=order.limit_price, fee=fee, ts=utcnow()))
            else:
                still.append(order)
        self._resting = still
