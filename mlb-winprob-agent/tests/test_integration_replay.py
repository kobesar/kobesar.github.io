"""Integration test: replay a recorded session through the full stack and
assert the resulting decision log matches a committed golden file.

Regenerate the golden after intentional behavior changes:
    python tests/test_integration_replay.py --regen
"""
import json
import sys
import tempfile
from pathlib import Path

from agent.clock import ReplayClock
from agent.config import load_config
from agent.core import Agent
from agent.execution.paper import PaperExecutor
from agent.fairvalue.estimator import FairValueEstimator
from agent.fairvalue.we_table import WeTable
from agent.ingest.replay import replay
from agent.obs.logger import DecisionLogger
from agent.risk.gate import RiskGate
from agent.signal.engine import SignalEngine

FIXT = Path(__file__).parent / "fixtures" / "session.jsonl"
GOLDEN = Path(__file__).parent / "fixtures" / "golden.json"


def run_stack() -> list[dict]:
    cfg = load_config("config.yaml")
    table = WeTable.load(cfg.fairvalue.we_table_path, cfg.fairvalue.min_cell_n)
    est = FairValueEstimator(table, cfg.fairvalue, cfg.market.pregame_prior)
    signal = SignalEngine(cfg.signal)
    executor = PaperExecutor(cfg.execution)
    risk = RiskGate(cfg.risk, cfg.feeds.book_staleness_seconds, cfg.signal.max_state_age)
    clock = ReplayClock()
    tmp = tempfile.mkdtemp()
    logger = DecisionLogger(0, "test", log_dir=tmp)
    agent = Agent(cfg, est, signal, executor, risk, logger)

    out = []
    for tick in replay(FIXT, speed=0, clock=clock):
        now = clock.now()
        d = agent.process_tick(tick.game_state, tick.book, now)
        out.append({
            "action": d.action,
            "reason": d.reason,
            "position": round(d.position, 4),
            "realized": round(d.realized_pnl, 4),
            "marked": round(d.marked_pnl, 4),
        })
    logger.close()
    return out


def test_replay_matches_golden():
    expected = json.loads(GOLDEN.read_text())
    actual = run_stack()
    assert len(actual) == len(expected)
    for i, (a, e) in enumerate(zip(actual, expected)):
        assert a == e, f"tick {i} mismatch:\n  got={a}\n  exp={e}"


def test_kill_switch_flattens_mid_replay(tmp_path):
    """A KILL file mid-session halts and flattens (paper)."""
    cfg = load_config("config.yaml")
    kill = tmp_path / "KILL"
    cfg = cfg.model_copy(update={"risk": cfg.risk.model_copy(update={"kill_file": str(kill)})})
    table = WeTable.load(cfg.fairvalue.we_table_path, cfg.fairvalue.min_cell_n)
    est = FairValueEstimator(table, cfg.fairvalue, cfg.market.pregame_prior)
    executor = PaperExecutor(cfg.execution)
    risk = RiskGate(cfg.risk, cfg.feeds.book_staleness_seconds, cfg.signal.max_state_age)
    clock = ReplayClock()
    logger = DecisionLogger(0, "kill", log_dir=str(tmp_path))
    agent = Agent(cfg, est, SignalEngine(cfg.signal), executor, risk, logger)

    halted = False
    for i, tick in enumerate(replay(FIXT, speed=0, clock=clock)):
        if i == 60:
            kill.write_text("")  # arm the kill switch mid-session
        d = agent.process_tick(tick.game_state, tick.book, clock.now())
        if d.action == "halt":
            halted = True
            assert d.position == 0.0  # flattened
    logger.close()
    assert halted and risk.halted


if __name__ == "__main__":
    if "--regen" in sys.argv:
        GOLDEN.write_text(json.dumps(run_stack(), indent=0))
        print(f"regenerated golden: {GOLDEN}")
