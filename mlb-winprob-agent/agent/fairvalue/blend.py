"""Pregame-prior blending.

Early in the game the state-based WE is noisy and ignores team strength, so we
blend it with a manually-entered pregame prior. The weight on the state WE
ramps linearly from `w_start` at inning 1 to 1.0 at `full_inning`.
"""
from __future__ import annotations


def blend_weight(inning: int, w_start: float, full_inning: int) -> float:
    if full_inning <= 1:
        return 1.0
    if inning >= full_inning:
        return 1.0
    if inning <= 1:
        return w_start
    frac = (inning - 1) / (full_inning - 1)
    return w_start + (1.0 - w_start) * frac


def blend(state_we: float, pregame_prior: float, w: float) -> float:
    return w * state_we + (1.0 - w) * pregame_prior
