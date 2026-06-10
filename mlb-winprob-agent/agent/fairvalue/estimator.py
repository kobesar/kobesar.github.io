"""GameState -> FairValue.

Combines the WE table lookup with the pregame-prior blend and clamps the
result. If the game is final the fair value is exactly 0 or 1.
"""
from __future__ import annotations

from ..clock import utcnow
from ..config import FairValueCfg
from ..models import FairValue, GameState
from .blend import blend, blend_weight
from .we_table import WeTable


class FairValueEstimator:
    def __init__(self, table: WeTable, cfg: FairValueCfg, pregame_prior: float) -> None:
        self.table = table
        self.cfg = cfg
        self.pregame_prior = pregame_prior

    def estimate(self, gs: GameState) -> FairValue:
        now = utcnow()
        w = blend_weight(gs.lookup_inning, self.cfg.blend_w_start, self.cfg.blend_full_inning)

        if gs.status == "final":
            prob = 1.0 if gs.home_score > gs.away_score else 0.0
            return FairValue(
                prob=prob, effective_n=1e9, state_we=prob,
                pregame_prior=self.pregame_prior, blend_weight=1.0, computed_at=now,
            )

        look = self.table.lookup(gs.lookup_inning, gs.half, gs.outs, gs.base_state, gs.score_diff)
        fv = blend(look.prob, self.pregame_prior, w)
        fv = min(self.cfg.clamp_high, max(self.cfg.clamp_low, fv))
        return FairValue(
            prob=fv,
            effective_n=look.effective_n,
            state_we=look.prob,
            pregame_prior=self.pregame_prior,
            blend_weight=w,
            computed_at=now,
        )
