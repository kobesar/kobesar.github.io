"""Synthetic game + market generator (behind the --mock flag).

This is MOCK DATA, clearly labeled. The live MLB and Polymarket feeds are
firewalled in this build environment (see README section 2), so this generator
lets the entire stack run end-to-end: it simulates a game progressing plate
appearance by plate appearance and a market whose mid *lags* true win
probability by a few seconds. The lag is deliberate and realistic -- it both
creates the transient edges the agent trades and demonstrates the central
finding that the market usually leads our state-derived fair value.
"""
from __future__ import annotations

import random
from datetime import timedelta
from typing import Iterator, Optional

from ..clock import utcnow
from ..models import BookState, GameState
from .replay import ReplayTick

# plate-appearance outcome model (league-ish), used only to advance the sim
_OUTCOMES = [
    ("out", 0.690), ("bb", 0.085), ("1b", 0.145),
    ("2b", 0.045), ("3b", 0.004), ("hr", 0.031),
]


def _advance(bases: list[bool], outs: int, event: str) -> tuple[list[bool], int, int]:
    b1, b2, b3 = bases
    runs = 0
    if event == "out":
        return [b1, b2, b3], outs + 1, 0
    if event == "bb":
        if not b1:
            b1 = True
        elif not b2:
            b2 = True
        elif not b3:
            b3 = True
        else:
            runs += 1
        return [b1, b2, b3], outs, runs
    if event == "1b":
        runs += int(b3) + int(b2)
        return [True, False, b1], outs, runs
    if event == "2b":
        runs += int(b3) + int(b2)
        return [False, True, b1], outs, runs
    if event == "3b":
        runs += int(b1) + int(b2) + int(b3)
        return [False, False, True], outs, runs
    # hr
    runs += 1 + int(b1) + int(b2) + int(b3)
    return [False, False, False], outs, runs


def _draw(rng: random.Random) -> str:
    r = rng.random()
    acc = 0.0
    for ev, p in _OUTCOMES:
        acc += p
        if r <= acc:
            return ev
    return "out"


def _base_mask(bases: list[bool]) -> int:
    return int(bases[0]) | (int(bases[1]) << 1) | (int(bases[2]) << 2)


def simulate_states(game_pk: int, rng: random.Random, max_plate: int = 90) -> list[dict]:
    """Return an ordered list of distinct game states (as dicts) for one game."""
    inning, half = 1, "top"
    outs = 0
    bases = [False, False, False]
    home, away = 0, 0
    states: list[dict] = []

    def snapshot(status: str = "live") -> None:
        states.append(dict(inning=inning, half=half, outs=outs,
                           base_state=_base_mask(bases), home_score=home,
                           away_score=away, status=status))

    snapshot()
    for _ in range(max_plate * 6):
        ev = _draw(rng)
        bases, outs, runs = _advance(bases, outs, ev)
        if half == "top":
            away += runs
        else:
            home += runs
        if outs >= 3:
            # half-inning over
            outs = 0
            bases = [False, False, False]
            if half == "top":
                half = "bottom"
            else:
                half = "top"
                inning += 1
            # walk-off / regulation end checks
            if inning >= 10 and half == "top" and home > away:
                break
        snapshot()
        if half == "bottom" and inning >= 9 and home > away:
            break  # walk-off
        if inning > 11:
            break
    # final
    inning_final = inning
    states.append(dict(inning=inning_final, half=half, outs=outs,
                       base_state=0, home_score=home, away_score=away, status="final"))
    return states


def mock_session(game_pk: int, market_id: str, *, seed: int = 7,
                 tick_seconds: float = 3.0, holds_per_state: int = 2,
                 market_lag_ticks: int = 3, noise_cents: float = 0.01,
                 staleness_limit: float = 10.0, start=None,
                 estimate_fn=None) -> Iterator[ReplayTick]:
    """Yield ReplayTicks. `estimate_fn(GameState)->prob` supplies 'true' WP used
    to build a *lagged* market mid. If None, a crude diff heuristic is used.
    Pass `start` (datetime) for deterministic timestamps."""
    rng = random.Random(seed)
    states = simulate_states(game_pk, rng)
    start = start or utcnow()
    true_hist: list[float] = []
    tick_i = 0

    def fair(gs: GameState) -> float:
        if estimate_fn is not None:
            return estimate_fn(gs)
        return min(0.97, max(0.03, 0.5 + 0.06 * gs.score_diff))

    for st in states:
        for _ in range(holds_per_state):
            ts = start + timedelta(seconds=tick_seconds * tick_i)
            gs = GameState(game_pk=game_pk, ingested_at=ts, source_ts=ts, **st)
            true_wp = fair(gs)
            true_hist.append(true_wp)
            lagged = true_hist[max(0, len(true_hist) - 1 - market_lag_ticks)]
            mid = lagged + rng.gauss(0.0, noise_cents)
            mid = min(0.98, max(0.02, mid))
            half_spread = 0.01
            best_bid = round(mid - half_spread, 2)
            best_ask = round(mid + half_spread, 2)
            book = BookState(
                market_id=market_id,
                best_bid=best_bid,
                best_ask=best_ask,
                bid_depth={best_bid: 1500.0, round(best_bid - 0.01, 2): 2500.0},
                ask_depth={best_ask: 1500.0, round(best_ask + 0.01, 2): 2500.0},
                last_update=ts,
                staleness_limit=staleness_limit,
            )
            yield ReplayTick(ts, gs, book)
            tick_i += 1
