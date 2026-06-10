"""Win-expectancy table lookup with shrinkage toward neighboring score_diff cells.

The table is keyed by (inning, half, outs, base_state, score_diff). Sparse cells
(n < min_cell_n) are shrunk toward the n-weighted average of the adjacent
score_diff cells so we never trust a thin cell at face value.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

Key = tuple[int, str, int, int, int]


@dataclass(frozen=True)
class Cell:
    win_prob: float
    n: float


@dataclass(frozen=True)
class Lookup:
    prob: float
    effective_n: float
    raw: float          # raw cell value before shrinkage (== prob if cell missing)


class WeTable:
    def __init__(self, cells: dict[Key, Cell], min_cell_n: int = 200) -> None:
        self._cells = cells
        self.min_cell_n = min_cell_n

    @classmethod
    def load(cls, path: str | Path, min_cell_n: int = 200) -> "WeTable":
        path = Path(path)
        cells: dict[Key, Cell] = {}
        with path.open() as f:
            for row in csv.DictReader(f):
                key: Key = (
                    int(row["inning"]),
                    row["half"],
                    int(row["outs"]),
                    int(row["base_state"]),
                    int(row["score_diff"]),
                )
                cells[key] = Cell(float(row["win_prob"]), float(row["n"]))
        if not cells:
            raise ValueError(f"empty WE table: {path}")
        return cls(cells, min_cell_n)

    @staticmethod
    def _norm(inning: int, half: str, outs: int, base: int, diff: int) -> Key:
        inning = 10 if inning >= 10 else inning
        diff = max(-6, min(6, diff))
        return (inning, half, outs, base, diff)

    def _neighbor_avg(self, key: Key) -> tuple[float | None, float]:
        """n-weighted average of the score_diff-adjacent cells. Returns
        (prob_or_None, total_n)."""
        inning, half, outs, base, diff = key
        num = 0.0
        den = 0.0
        for dd in (diff - 1, diff + 1):
            if not (-6 <= dd <= 6):
                continue
            c = self._cells.get((inning, half, outs, base, dd))
            if c is None:
                continue
            num += c.win_prob * c.n
            den += c.n
        if den == 0:
            return None, 0.0
        return num / den, den

    def lookup(self, inning: int, half: str, outs: int, base: int, diff: int) -> Lookup:
        key = self._norm(inning, half, outs, base, diff)
        cell = self._cells.get(key)
        neigh_p, neigh_n = self._neighbor_avg(key)

        if cell is None:
            # missing cell entirely -> neighbor average, effective_n = 0
            if neigh_p is None:
                # nothing nearby at all; fall back to a coin flip
                return Lookup(prob=0.5, effective_n=0.0, raw=0.5)
            return Lookup(prob=neigh_p, effective_n=0.0, raw=neigh_p)

        if cell.n >= self.min_cell_n or neigh_p is None:
            return Lookup(prob=cell.win_prob, effective_n=cell.n, raw=cell.win_prob)

        # shrink toward neighbor average with k = min_cell_n
        k = float(self.min_cell_n)
        p_hat = (cell.n * cell.win_prob + k * neigh_p) / (cell.n + k)
        return Lookup(prob=p_hat, effective_n=cell.n + k, raw=cell.win_prob)
