#!/usr/bin/env python3
"""Entrypoint for the MLB win-probability paper-trading agent.

  python run.py --game <gamePk> --market <token_id>      # live (paper) mode
  python run.py --replay logs/<file>.jsonl --speed 10    # replay a session
  python run.py --mock --game 0 --market MOCK            # synthetic end-to-end

Live order placement is NOT implemented (paper trading is the product). If
mode: live is set in config, the run loop refuses to start because the live
executor is a stub (see README Phase 3 gate).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from agent.clock import Clock, ReplayClock, utcnow
from agent.config import load_config
from agent.core import Agent
from agent.execution.live_stub import LiveStubExecutor
from agent.execution.paper import PaperExecutor
from agent.fairvalue.estimator import FairValueEstimator
from agent.fairvalue.we_table import WeTable
from agent.obs.dashboard import Dashboard
from agent.obs.logger import DecisionLogger
from agent.risk.gate import RiskGate
from agent.signal.engine import SignalEngine


def build_agent(cfg, game_pk, market_id):
    table = WeTable.load(cfg.fairvalue.we_table_path, cfg.fairvalue.min_cell_n)
    estimator = FairValueEstimator(table, cfg.fairvalue, cfg.market.pregame_prior)
    signal = SignalEngine(cfg.signal)

    if cfg.mode == "live":
        executor = LiveStubExecutor()
    else:
        executor = PaperExecutor(cfg.execution)

    risk = RiskGate(cfg.risk, cfg.feeds.book_staleness_seconds, cfg.signal.max_state_age)
    logger = DecisionLogger(game_pk, market_id, snapshot_every_seconds=cfg.book_snapshot_every_seconds)
    agent = Agent(cfg, estimator, signal, executor, risk, logger)
    return agent, estimator, logger


def _refuse_if_live_stub(cfg) -> None:
    if cfg.mode == "live" and isinstance(LiveStubExecutor(), LiveStubExecutor):
        print("ERROR: mode 'live' uses the live executor stub, which is not "
              "implemented. This is a paper-trading build. Set mode: paper in "
              "config.yaml. See README Phase 3 gate.", file=sys.stderr)
        sys.exit(2)


def run_replay(cfg, args) -> None:
    from agent.ingest.replay import replay

    # infer game_pk/market from filename when possible
    name = Path(args.replay).stem
    game_pk = args.game if args.game is not None else 0
    market_id = args.market or (name.split("_", 2)[-1] if "_" in name else "REPLAY")
    clock = ReplayClock()
    agent, _, logger = build_agent(cfg, game_pk, f"replay_{market_id}")
    dash = Dashboard(cfg, enabled=not args.no_dashboard)
    n = 0
    with dash:
        for tick in replay(args.replay, speed=args.speed, clock=clock):
            now = clock.now()
            decision = agent.process_tick(tick.game_state, tick.book, now)
            dash.update(decision, Path(cfg.risk.kill_file).exists(), agent.risk.halt_reason, now)
            n += 1
            if args.max_ticks and n >= args.max_ticks:
                break
    logger.close()
    print(f"replayed {n} ticks; final pnl = {agent.executor.pnl()}")


def run_mock(cfg, args) -> None:
    from agent.ingest.mock import mock_session

    game_pk = args.game if args.game is not None else 0
    market_id = args.market or "MOCK"
    clock = ReplayClock()
    agent, estimator, logger = build_agent(cfg, game_pk, market_id)
    dash = Dashboard(cfg, enabled=not args.no_dashboard)
    n = 0
    with dash:
        for tick in mock_session(game_pk, market_id,
                                 staleness_limit=cfg.feeds.book_staleness_seconds,
                                 estimate_fn=lambda gs: estimator.estimate(gs).prob):
            clock.set(tick.ts)
            now = clock.now()
            decision = agent.process_tick(tick.game_state, tick.book, now)
            dash.update(decision, Path(cfg.risk.kill_file).exists(), agent.risk.halt_reason, now)
            n += 1
            if args.speed and args.speed > 0 and not args.no_dashboard:
                time.sleep(min(3.0 / args.speed, 0.3))
            if args.max_ticks and n >= args.max_ticks:
                break
    logger.close()
    print(f"mock session: {n} ticks; final pnl = {agent.executor.pnl()}; "
          f"log = {logger.decision_path}")


def run_live(cfg, args) -> None:
    _refuse_if_live_stub(cfg)
    from agent.ingest.clob_feed import ClobFeed
    from agent.ingest.mlb_feed import MlbFeed

    if args.game is None or not args.market:
        print("ERROR: live mode requires --game <gamePk> and --market <token_id>", file=sys.stderr)
        sys.exit(2)

    clock = Clock()
    agent, _, logger = build_agent(cfg, args.game, cfg.market.market_id)
    mlb = MlbFeed(args.game, cfg.feeds.statsapi_base, cfg.feeds.mlb_poll_seconds)
    clob = ClobFeed(args.market, cfg.market.market_id, cfg.feeds.clob_ws_url,
                    cfg.feeds.clob_rest_url, cfg.feeds.book_staleness_seconds)
    mlb.start()
    clob.start_rest_poll()  # REST fallback; swap to asyncio run_ws() when reachable
    dash = Dashboard(cfg, enabled=not args.no_dashboard)
    n = 0
    try:
        with dash:
            while True:
                gs = mlb.latest()
                book = clob.latest()
                if gs is not None and book is not None:
                    now = clock.now()
                    decision = agent.process_tick(gs, book, now)
                    dash.update(decision, Path(cfg.risk.kill_file).exists(),
                                agent.risk.halt_reason, now)
                    n += 1
                    if gs.status == "final":
                        break
                if args.max_ticks and n >= args.max_ticks:
                    break
                time.sleep(cfg.feeds.mlb_poll_seconds)
    except KeyboardInterrupt:
        pass
    finally:
        mlb.stop()
        clob.stop()
        logger.close()
    print(f"live session ended: {n} ticks; final pnl = {agent.executor.pnl()}")


def main() -> None:
    ap = argparse.ArgumentParser(description="MLB win-probability paper-trading agent")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--game", type=int, default=None, help="MLB gamePk")
    ap.add_argument("--market", default=None, help="Polymarket YES(home) token id")
    ap.add_argument("--replay", default=None, help="replay a logged JSONL session")
    ap.add_argument("--mock", action="store_true", help="run a synthetic game end-to-end")
    ap.add_argument("--speed", type=float, default=1.0, help="replay/mock speed multiplier")
    ap.add_argument("--no-dashboard", action="store_true")
    ap.add_argument("--max-ticks", type=int, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)

    if args.replay:
        run_replay(cfg, args)
    elif args.mock:
        run_mock(cfg, args)
    else:
        run_live(cfg, args)


if __name__ == "__main__":
    main()
