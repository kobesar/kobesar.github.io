"""Typed payloads that flow through the agent.

Every type carries timestamps. Latency is the enemy: any consumer can ask how
old a piece of data is and refuse to act on it.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .clock import utcnow

GameStatus = Literal["scheduled", "live", "final", "delayed", "unknown"]
Action = Literal["none", "enter_long", "enter_short", "exit", "halt"]


def _aware(ts: datetime) -> datetime:
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)


class GameState(BaseModel):
    game_pk: int
    inning: int = 1                      # 1-based
    half: Literal["top", "bottom"] = "top"
    outs: int = 0                        # 0-2
    base_state: int = 0                  # bitmask: 1B=1, 2B=2, 3B=4 -> 0..7
    home_score: int = 0
    away_score: int = 0
    status: GameStatus = "unknown"
    source_ts: Optional[datetime] = None  # feed's own timestamp if available
    ingested_at: datetime = Field(default_factory=utcnow)
    # set by the poller when this state differs from the previous one
    state_changed: bool = False

    def state_age_seconds(self, now: Optional[datetime] = None) -> float:
        now = now or utcnow()
        return (now - _aware(self.ingested_at)).total_seconds()

    @property
    def score_diff(self) -> int:
        """home - away, capped at +/-6 for table lookup."""
        d = self.home_score - self.away_score
        return max(-6, min(6, d))

    @property
    def lookup_inning(self) -> int:
        """Innings >= 10 collapse to a single 'extras' bucket (10)."""
        return 10 if self.inning >= 10 else self.inning

    def key(self) -> tuple[int, str, int, int, int]:
        return (self.lookup_inning, self.half, self.outs, self.base_state, self.score_diff)


class BookState(BaseModel):
    market_id: str
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    bid_depth: dict[float, float] = Field(default_factory=dict)  # price -> size
    ask_depth: dict[float, float] = Field(default_factory=dict)
    last_update: datetime = Field(default_factory=utcnow)
    staleness_limit: float = 10.0  # seconds; set from config at construction

    @property
    def mid(self) -> Optional[float]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2.0

    @property
    def spread(self) -> Optional[float]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    def age_seconds(self, now: Optional[datetime] = None) -> float:
        now = now or utcnow()
        return (now - _aware(self.last_update)).total_seconds()

    def is_stale(self, now: Optional[datetime] = None) -> bool:
        if self.best_bid is None or self.best_ask is None:
            return True
        return self.age_seconds(now) > self.staleness_limit

    def depth_within(self, center: float, cents: float, side: Literal["bid", "ask"]) -> float:
        """Total size within `cents` of `center` on the given side."""
        book = self.bid_depth if side == "bid" else self.ask_depth
        return sum(sz for px, sz in book.items() if abs(px - center) <= cents + 1e-9)


class FairValue(BaseModel):
    prob: float                  # home-team win probability
    effective_n: float           # sample size behind the lookup cell
    state_we: float              # raw table value
    pregame_prior: float
    blend_weight: float
    computed_at: datetime = Field(default_factory=utcnow)


class Order(BaseModel):
    side: Literal["buy", "sell"]   # buy = go long home, sell = go short home
    size: float                    # shares (contracts)
    limit_price: Optional[float] = None  # None => market-style sweep
    reason: str = ""
    ts: datetime = Field(default_factory=utcnow)


class Fill(BaseModel):
    side: Literal["buy", "sell"]
    size: float
    price: float                   # all-in price incl. slippage
    fee: float
    ts: datetime = Field(default_factory=utcnow)


class Decision(BaseModel):
    # one per tick, ALWAYS logged, even when action == "none"
    ts: datetime = Field(default_factory=utcnow)
    game_state: GameState
    book: BookState
    fair_value: Optional[FairValue] = None
    edge: Optional[float] = None
    action: Action = "none"
    reason: str = ""
    position: float = 0.0
    avg_entry: Optional[float] = None
    realized_pnl: float = 0.0
    marked_pnl: float = 0.0
