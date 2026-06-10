"""Config loading + validation.

ALL tunables live in config.yaml. We validate with pydantic at startup and
refuse to run on unknown keys or on a config that breaks the hysteresis
invariant (entry_threshold must exceed exit_threshold).
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Strict(BaseModel):
    # forbid unknown keys anywhere in the tree
    model_config = ConfigDict(extra="forbid")


class MarketCfg(_Strict):
    market_id: str = "MOCK-MLB"
    token_id: str = ""               # Polymarket ERC1155 token id for the YES(home) outcome
    pregame_prior: float = 0.5       # de-vigged home win prob, entered manually


class FeedsCfg(_Strict):
    mlb_poll_seconds: float = 3.0
    book_staleness_seconds: float = 10.0
    clob_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    clob_rest_url: str = "https://clob.polymarket.com"
    statsapi_base: str = "https://statsapi.mlb.com"


class FairValueCfg(_Strict):
    we_table_path: str = "data/we_table.csv"
    min_cell_n: int = 200
    blend_w_start: float = 0.35
    blend_full_inning: int = 7
    clamp_low: float = 0.02
    clamp_high: float = 0.98


class SignalCfg(_Strict):
    entry_threshold: float = 0.04
    exit_threshold: float = 0.015
    max_state_age: float = 20.0       # refuse to trade if GameState older than this
    max_spread: float = 0.03
    min_depth: float = 100.0
    depth_band_cents: float = 0.02
    post_change_cooldown: float = 8.0
    no_trade_from_inning: int = 9
    max_hold_seconds: float = 600.0
    per_position_stop: float = 30.0   # USD adverse mark before forced exit
    order_size: float = 400.0         # shares per entry


class ExecutionCfg(_Strict):
    taker_fee: float = 0.0            # fraction of notional per fill
    extra_slippage_cents: float = 0.01
    maker_mode: bool = False


class RiskCfg(_Strict):
    max_position_shares: float = 1000.0
    max_position_usd: float = 600.0
    max_total_usd: float = 500.0
    per_game_loss_limit: float = 75.0
    daily_loss_limit: float = 200.0
    max_fv_jump: float = 0.15
    max_orders_per_minute: int = 6
    kill_file: str = "./KILL"
    feed_disagreement_seconds: float = 30.0


class Config(_Strict):
    mode: Literal["paper", "live"] = "paper"
    market: MarketCfg = Field(default_factory=MarketCfg)
    feeds: FeedsCfg = Field(default_factory=FeedsCfg)
    fairvalue: FairValueCfg = Field(default_factory=FairValueCfg)
    signal: SignalCfg = Field(default_factory=SignalCfg)
    execution: ExecutionCfg = Field(default_factory=ExecutionCfg)
    risk: RiskCfg = Field(default_factory=RiskCfg)
    book_snapshot_every_seconds: float = 30.0

    @model_validator(mode="after")
    def _check_hysteresis(self) -> "Config":
        if self.signal.entry_threshold <= self.signal.exit_threshold:
            raise ValueError(
                "signal.entry_threshold (%.4f) must be > signal.exit_threshold (%.4f)"
                % (self.signal.entry_threshold, self.signal.exit_threshold)
            )
        if not (0.0 <= self.fairvalue.clamp_low < self.fairvalue.clamp_high <= 1.0):
            raise ValueError("fairvalue clamp bounds invalid")
        return self


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    raw = yaml.safe_load(path.read_text()) or {}
    return Config.model_validate(raw)
