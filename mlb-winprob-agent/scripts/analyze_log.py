#!/usr/bin/env python3
"""Post-game analysis of decision logs.

  python scripts/analyze_log.py logs/*.jsonl

Produces:
  * calibration: bucketed fair value vs realized outcome, our Brier score, and
    the market's Brier on the same ticks (the benchmark to beat)
  * lead-lag: cross-correlation of fv changes vs mid changes at lags -60..+60s.
    If the market leads our fv, that is said loudly -- it means our "edge" is
    latency, not insight.
  * paper PnL: per-game total (net of fees/slippage), hit rate, avg win/loss,
    max drawdown
  * threshold sweep: counterfactual PnL vs entry_threshold over the logged ticks
    (in-sample, clearly labeled)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np


def load(path: str) -> list[dict]:
    out = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def game_outcome(records: list[dict]) -> float | None:
    """Eventual home win (1.0/0.0) from the last record, if the game finished."""
    last = records[-1]
    gs = last["game_state"]
    if gs.get("status") == "final" or last.get("fair_value", {}) and last["game_state"]["status"] == "final":
        return 1.0 if gs["home_score"] > gs["away_score"] else 0.0
    # fall back to the leading team at the last tick (labeled as provisional)
    return None


def series(records: list[dict]):
    ts, fv, mid, real, marked, edge = [], [], [], [], [], []
    for r in records:
        b = r["book"]
        m = None
        if b.get("best_bid") is not None and b.get("best_ask") is not None:
            m = (b["best_bid"] + b["best_ask"]) / 2.0
        f = r["fair_value"]["prob"] if r.get("fair_value") else None
        ts.append(datetime.fromisoformat(r["ts"]).timestamp())
        fv.append(f)
        mid.append(m)
        real.append(r.get("realized_pnl", 0.0))
        marked.append(r.get("marked_pnl", 0.0))
        edge.append(r.get("edge"))
    return (np.array(ts), fv, mid, np.array(real), np.array(marked), edge)


def calibration(all_recs: list[list[dict]]) -> None:
    print("\n=== CALIBRATION ===")
    fvs, mids, ys = [], [], []
    for recs in all_recs:
        y = game_outcome(recs)
        if y is None:
            continue
        for r in recs:
            f = r["fair_value"]["prob"] if r.get("fair_value") else None
            b = r["book"]
            m = (b["best_bid"] + b["best_ask"]) / 2.0 if b.get("best_bid") is not None and b.get("best_ask") is not None else None
            if f is None or m is None:
                continue
            fvs.append(f); mids.append(m); ys.append(y)
    if not fvs:
        print("  no finished-game ticks to calibrate on.")
        return
    fvs = np.array(fvs); mids = np.array(mids); ys = np.array(ys)
    print(f"  ticks: {len(ys)}")
    edges = np.linspace(0, 1, 11)
    print("  bucket      n     mean_fv   emp_win")
    for i in range(10):
        lo, hi = edges[i], edges[i + 1]
        m = (fvs >= lo) & (fvs < hi if i < 9 else fvs <= hi)
        if m.sum() == 0:
            continue
        print(f"  [{lo:.1f},{hi:.1f})  {m.sum():5d}   {fvs[m].mean():.3f}    {ys[m].mean():.3f}")
    brier_fv = float(np.mean((fvs - ys) ** 2))
    brier_mkt = float(np.mean((mids - ys) ** 2))
    print(f"  Brier  ours={brier_fv:.4f}   market={brier_mkt:.4f}   "
          f"({'we beat market' if brier_fv < brier_mkt else 'market beats us'})")


def lead_lag(all_recs: list[list[dict]]) -> None:
    print("\n=== LEAD-LAG (fv change vs mid change) ===")
    best_overall = []
    for recs in all_recs:
        ts, fv, mid, *_ = series(recs)
        pairs = [(t, f, m) for t, f, m in zip(ts, fv, mid) if f is not None and m is not None]
        if len(pairs) < 30:
            continue
        t = np.array([p[0] for p in pairs])
        f = np.array([p[1] for p in pairs])
        m = np.array([p[2] for p in pairs])
        # resample to a uniform 1s grid (forward fill) so lags are in seconds
        grid = np.arange(int(t[0]), int(t[-1]) + 1)
        fi = np.interp(grid, t, f)
        mi = np.interp(grid, t, m)
        df = np.diff(fi); dm = np.diff(mi)
        if df.std() < 1e-9 or dm.std() < 1e-9:
            continue
        lags = range(-60, 61)
        corrs = []
        for lag in lags:
            if lag >= 0:
                a, b = df[: len(df) - lag], dm[lag:]
            else:
                a, b = df[-lag:], dm[: len(dm) + lag]
            if len(a) < 10 or a.std() < 1e-9 or b.std() < 1e-9:
                corrs.append(0.0)
            else:
                corrs.append(float(np.corrcoef(a, b)[0, 1]))
        corrs = np.array(corrs)
        best_lag = list(lags)[int(np.argmax(corrs))]
        best_overall.append(best_lag)
        print(f"  game ({len(pairs)} ticks): peak corr {corrs.max():.3f} at lag "
              f"{best_lag:+d}s")
    if best_overall:
        mean_lag = float(np.mean(best_overall))
        print(f"  mean peak lag = {mean_lag:+.1f}s")
        if mean_lag > 2:
            print("  => fv changes LEAD mid changes: state-derived signal moves first "
                  "(potential edge, if fills are fast enough).")
        elif mean_lag < -2:
            print("  => MARKET LEADS our fv: our 'edge' is mostly latency. "
                  "Be skeptical of paper PnL.")
        else:
            print("  => roughly contemporaneous: no clear lead-lag edge.")


def pnl_report(all_recs: list[list[dict]]) -> None:
    print("\n=== PAPER PnL ===")
    totals = []
    for recs in all_recs:
        _, _, _, real, marked, _ = series(recs)
        total = float(real[-1] + marked[-1])
        totals.append(total)
        # per-trade outcomes from realized jumps
        dreal = np.diff(real)
        trades = dreal[np.abs(dreal) > 1e-6]
        wins = trades[trades > 0]; losses = trades[trades < 0]
        cum = real + marked
        peak = np.maximum.accumulate(cum)
        max_dd = float((cum - peak).min()) if len(cum) else 0.0
        hit = (len(wins) / len(trades) * 100) if len(trades) else 0.0
        print(f"  game: total ${total:+.2f}  trades={len(trades)}  hit={hit:.0f}%  "
              f"avg_win ${wins.mean() if len(wins) else 0:+.2f}  "
              f"avg_loss ${losses.mean() if len(losses) else 0:+.2f}  "
              f"maxDD ${max_dd:.2f}")
    if totals:
        t = np.array(totals)
        print(f"  across {len(t)} games: mean ${t.mean():+.2f}  total ${t.sum():+.2f}  "
              f"std ${t.std():.2f}")


def threshold_sweep(all_recs: list[list[dict]], exit_thr: float = 0.015,
                    size: float = 400.0) -> None:
    print("\n=== THRESHOLD SWEEP (counterfactual, IN-SAMPLE) ===")
    print("  Rough sim on logged mids; ignores depth/fees. Treat as indicative only.")
    print("  entry_thr    pnl($)    trades")
    for thr in (0.02, 0.03, 0.04, 0.05, 0.07, 0.10):
        total = 0.0
        trades = 0
        for recs in all_recs:
            pos = 0      # +1 long, -1 short
            entry_mid = 0.0
            for r in recs:
                e = r.get("edge")
                b = r["book"]
                m = (b["best_bid"] + b["best_ask"]) / 2.0 if b.get("best_bid") is not None and b.get("best_ask") is not None else None
                if e is None or m is None:
                    continue
                if pos == 0:
                    if e > thr:
                        pos, entry_mid = 1, m
                    elif e < -thr:
                        pos, entry_mid = -1, m
                else:
                    if abs(e) < exit_thr:
                        total += (m - entry_mid) * pos * size
                        trades += 1
                        pos = 0
            # close any open position at last mid
        print(f"  {thr:.2f}        {total:+8.1f}   {trades}")


def main() -> None:
    paths = sys.argv[1:]
    if not paths:
        print("usage: python scripts/analyze_log.py logs/*.jsonl", file=sys.stderr)
        sys.exit(2)
    all_recs = [load(p) for p in paths if Path(p).exists() and load(p)]
    all_recs = [r for r in all_recs if r]
    if not all_recs:
        print("no records found.", file=sys.stderr)
        sys.exit(1)
    print(f"loaded {len(all_recs)} log file(s), "
          f"{sum(len(r) for r in all_recs)} total ticks")
    calibration(all_recs)
    lead_lag(all_recs)
    pnl_report(all_recs)
    threshold_sweep(all_recs)


if __name__ == "__main__":
    main()
