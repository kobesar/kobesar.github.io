"""Executor interface. The run loop talks only to this; paper vs live is a
config-gated choice."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..models import BookState, Fill, Order


class Executor(ABC):
    @abstractmethod
    def submit(self, order: Order) -> list[Fill]:
        """Attempt to execute an order; return the fills that occurred."""

    @abstractmethod
    def cancel_all(self) -> None:
        ...

    @abstractmethod
    def update_market(self, book: BookState) -> None:
        """Feed the latest book so marks (and maker fills) stay current."""

    @abstractmethod
    def position(self) -> float:
        """Signed shares: >0 long home, <0 short home."""

    @property
    @abstractmethod
    def avg_entry(self) -> Optional[float]:
        ...

    @abstractmethod
    def pnl(self) -> dict:
        """{'realized': float, 'marked': float, 'total': float}."""
