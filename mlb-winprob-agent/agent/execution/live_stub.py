"""Live executor STUB.

Phase 3 only. This intentionally does nothing but raise. Live order placement,
wallet connection, and key management are explicitly out of scope for this
build (see README "Phase 3 gate"). The run loop refuses to start if
mode == 'live' and the executor is this stub.
"""
from __future__ import annotations

from typing import Optional

from ..models import BookState, Fill, Order
from .base import Executor

_PHASE3 = (
    "Live execution is not implemented. This is a paper-trading build. "
    "See README 'Phase 3 gate': implement order signing/placement against the "
    "exchange API, add wallet/key management, and remove this stub before "
    "enabling mode: live."
)


class LiveStubExecutor(Executor):
    def submit(self, order: Order) -> list[Fill]:
        raise NotImplementedError(_PHASE3)

    def cancel_all(self) -> None:
        raise NotImplementedError(_PHASE3)

    def update_market(self, book: BookState) -> None:
        raise NotImplementedError(_PHASE3)

    def position(self) -> float:
        raise NotImplementedError(_PHASE3)

    @property
    def avg_entry(self) -> Optional[float]:
        raise NotImplementedError(_PHASE3)

    def pnl(self) -> dict:
        raise NotImplementedError(_PHASE3)
