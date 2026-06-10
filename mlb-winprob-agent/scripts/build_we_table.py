#!/usr/bin/env python3
"""Build the win-expectancy (WE) table -> data/we_table.csv.

Keyed by (inning, half, outs, base_state, score_diff in [-6, 6]).
Innings >= 10 collapse to a single 'extras' bucket (inning=10).

SOURCE / METHODOLOGY
--------------------
This ships the *bootstrap* table the prompt allows. It is a parametric,
analytic win-expectancy model -- NOT empirical Retrosheet data. It is built
from:
  * a standard base-out run-expectancy (RE24) matrix for the value of the
    current partial half-inning, and
  * a normal approximation of total remaining run differential (each remaining
    full half-inning contributes mean ~0.5 runs, variance ~0.83), plus a small
    home-field edge and a tie -> extra-innings coin-flip.

It is smooth, monotone, and good enough to drive signal logic and to be
replaced later. Every value is synthetic; treat `n` as a *plausibility /
occupancy estimate*, not a real sample count.

RETROSHEET PATH (documented, not implemented here)
--------------------------------------------------
To build an empirical table instead:
  1. Download Retrosheet event files (2010-2024) from retrosheet.org.
  2. Parse with `chadwick` (cwevent) to play-by-play with base/out/score state.
  3. For each plate appearance, record (inning, half, outs, base_state,
     clamped score_diff) and the eventual game winner (home=1/0).
  4. Aggregate: win_prob = mean(home_won), n = count, per key.
  5. Collapse innings >= 10 to bucket 10. Write the same CSV schema.
Network access to retrosheet.org is required and is intentionally NOT done
automatically in this build.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "we_table.csv"

# Base-out run expectancy (runs scored in remainder of half-inning).
# base_state bitmask: 1B=1, 2B=2, 3B=4. Columns are outs 0,1,2.
RE: dict[int, tuple[float, float, float]] = {
    0: (0.481, 0.254, 0.098),   # empty
    1: (0.859, 0.509, 0.224),   # 1B
    2: (1.100, 0.664, 0.319),   # 2B
    3: (1.437, 0.884, 0.429),   # 1B 2B
    4: (1.350, 0.950, 0.353),   # 3B
    5: (1.784, 1.130, 0.478),   # 1B 3B
    6: (1.964, 1.376, 0.580),   # 2B 3B
    7: (2.292, 1.541, 0.752),   # loaded
}

MU_HALF = 0.50        # expected runs from a fresh half-inning
VAR_HALF = 0.83       # variance of runs in a half-inning
HOME_EDGE_RUNS = 0.12  # home-field advantage spread over remaining game
P_EXTRA_HOME = 0.52   # home win prob if tied entering extras (last at-bat edge)

# occupancy / plausibility weights for synthetic n
BASE_OCC = {0: 1.0, 1: 0.55, 2: 0.30, 3: 0.18, 4: 0.10, 5: 0.10, 6: 0.07, 7: 0.05}
N0 = 4200


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _remaining(inning: int, half: str) -> tuple[float, float]:
    """Return (home_full_halves, away_full_halves) still to be played,
    excluding the current partial half-inning."""
    if inning >= 10:  # extras bucket: treat as ~one extra inning of play left
        if half == "top":
            return 1.0, 0.0   # home will bat its bottom; away partial is current
        return 0.0, 0.0       # home batting now (walk-off pending), away done
    if half == "top":
        # away batting now (current partial). away full = tops of i+1..9.
        away_full = max(0, 9 - inning)
        # home full = bottoms of i..9 (home hasn't batted this inning yet).
        home_full = max(0, 10 - inning)
        return float(home_full), float(away_full)
    # bottom: home batting now (current partial). home full = bottoms i+1..9.
    home_full = max(0, 9 - inning)
    away_full = max(0, 9 - inning)  # tops of i+1..9
    return float(home_full), float(away_full)


def win_prob(inning: int, half: str, outs: int, base: int, diff: int) -> float:
    re_cur = RE[base][outs]
    home_full, away_full = _remaining(inning, half)
    home_batting = half == "bottom" or inning >= 10 and half == "bottom"

    home_mean = home_full * MU_HALF + (re_cur if half == "bottom" else 0.0)
    away_mean = away_full * MU_HALF + (re_cur if half == "top" else 0.0)

    innings_left = home_full + away_full + 1
    edge = HOME_EDGE_RUNS * min(1.0, innings_left / 17.0)
    m = diff + (home_mean - away_mean) + edge

    v = VAR_HALF * (home_full + away_full) + VAR_HALF  # + one partial half
    sd = math.sqrt(max(v, 1e-6))

    p_gt = 1.0 - _phi((0.5 - m) / sd)               # P(final diff >= 1)
    p_tie = _phi((0.5 - m) / sd) - _phi((-0.5 - m) / sd)
    p = p_gt + p_tie * P_EXTRA_HOME
    return min(0.99, max(0.01, p))


def synthetic_n(inning: int, outs: int, base: int, diff: int) -> int:
    diff_factor = math.exp(-abs(diff) / 2.5)
    inning_factor = 0.22 if inning >= 10 else 1.0 - 0.02 * inning
    out_factor = {0: 1.0, 1: 0.9, 2: 0.85}[outs]
    occ = diff_factor * inning_factor * out_factor * BASE_OCC[base]
    return max(1, round(N0 * occ))


def build_rows() -> list[dict]:
    rows = []
    innings = list(range(1, 10)) + [10]  # 10 == extras bucket
    for inning in innings:
        for half in ("top", "bottom"):
            for outs in (0, 1, 2):
                for base in range(8):
                    for diff in range(-6, 7):
                        rows.append({
                            "inning": inning,
                            "half": half,
                            "outs": outs,
                            "base_state": base,
                            "score_diff": diff,
                            "win_prob": round(win_prob(inning, half, outs, base, diff), 5),
                            "n": synthetic_n(inning, outs, base, diff),
                        })
    return rows


def main() -> None:
    rows = build_rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["inning", "half", "outs", "base_state", "score_diff", "win_prob", "n"]
        )
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} cells -> {OUT}")
    # quick sanity prints
    p_start = win_prob(1, "top", 0, 0, 0)
    print(f"  neutral game start (1 top 0out empty diff0) home WP = {p_start:.3f}")
    print(f"  bottom 9 empty 0out, home +1 = {win_prob(9, 'bottom', 0, 0, 1):.3f}")
    print(f"  top 9 empty 2out, away +1 (diff -1) = {win_prob(9, 'top', 2, 0, -1):.3f}")


if __name__ == "__main__":
    main()
