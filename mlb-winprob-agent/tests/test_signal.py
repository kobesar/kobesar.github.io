from datetime import timedelta

from agent.clock import utcnow
from agent.config import SignalCfg
from agent.models import BookState, FairValue, GameState
from agent.signal.engine import PositionView, SignalEngine

NOW = utcnow()


def gs(**kw):
    base = dict(game_pk=1, inning=5, half="top", outs=1, base_state=0,
                home_score=2, away_score=2, status="live", ingested_at=NOW)
    base.update(kw)
    return GameState(**base)


def book(mid=0.50, spread=0.02, depth=2000.0, age=0.0):
    bb = round(mid - spread / 2, 4)
    ba = round(mid + spread / 2, 4)
    return BookState(
        market_id="m", best_bid=bb, best_ask=ba,
        bid_depth={bb: depth}, ask_depth={ba: depth},
        last_update=NOW - timedelta(seconds=age), staleness_limit=10.0,
    )


def fv(prob):
    return FairValue(prob=prob, effective_n=1000, state_we=prob,
                     pregame_prior=0.5, blend_weight=1.0)


def engine():
    return SignalEngine(SignalCfg())


def flat():
    return PositionView()


def test_enter_long_on_positive_edge():
    e = engine()
    p = e.evaluate(gs(), book(mid=0.50), fv(0.60), flat(), NOW)
    assert p.action == "enter_long"
    assert p.edge > 0.04


def test_enter_short_on_negative_edge():
    e = engine()
    p = e.evaluate(gs(), book(mid=0.60), fv(0.50), flat(), NOW)
    assert p.action == "enter_short"


def test_edge_below_threshold_no_entry():
    e = engine()
    p = e.evaluate(gs(), book(mid=0.50), fv(0.52), flat(), NOW)
    assert p.action == "none"
    assert p.reason == "edge_below_threshold"


def test_hysteresis_hold_then_exit():
    e = engine()
    long_pos = PositionView(shares=400, avg_entry=0.50, marked_pnl=5.0, entry_ts=NOW)
    # edge between exit(0.015) and entry(0.04) -> keep holding
    hold = e.evaluate(gs(), book(mid=0.50), fv(0.53), long_pos, NOW)
    assert hold.action == "none" and hold.reason == "holding"
    # edge below exit threshold -> take profit
    out = e.evaluate(gs(), book(mid=0.50), fv(0.505), long_pos, NOW)
    assert out.action == "exit" and out.reason == "edge_reverted"


def test_stale_book_refusal():
    e = engine()
    p = e.evaluate(gs(), book(mid=0.50, age=30), fv(0.60), flat(), NOW)
    assert p.action == "none" and p.reason == "stale_book"


def test_stale_game_state_refusal():
    e = engine()
    old = gs(ingested_at=NOW - timedelta(seconds=25))
    p = e.evaluate(old, book(mid=0.50), fv(0.60), flat(), NOW)
    assert p.action == "none" and p.reason == "stale_game_state"


def test_post_change_cooldown():
    e = engine()
    g = gs(state_changed=True)
    p = e.evaluate(g, book(mid=0.50), fv(0.60), flat(), NOW)
    assert p.action == "none" and p.reason == "post_change_cooldown"


def test_no_trade_inning_blocks_entry():
    e = engine()
    p = e.evaluate(gs(inning=9), book(mid=0.50), fv(0.60), flat(), NOW)
    assert p.action == "none" and p.reason == "no_trade_inning"


def test_late_inning_flattens_position():
    e = engine()
    long_pos = PositionView(shares=400, avg_entry=0.50, marked_pnl=1.0, entry_ts=NOW)
    p = e.evaluate(gs(inning=9), book(mid=0.50), fv(0.60), long_pos, NOW)
    assert p.action == "exit" and p.reason == "late_inning_flatten"


def test_game_not_live_no_entry():
    e = engine()
    p = e.evaluate(gs(status="scheduled"), book(mid=0.50), fv(0.60), flat(), NOW)
    assert p.action == "none" and p.reason == "game_not_live"


def test_spread_too_wide():
    e = engine()
    p = e.evaluate(gs(), book(mid=0.50, spread=0.06), fv(0.60), flat(), NOW)
    assert p.action == "none" and p.reason == "spread_too_wide"


def test_insufficient_depth():
    e = engine()
    p = e.evaluate(gs(), book(mid=0.50, depth=10.0), fv(0.60), flat(), NOW)
    assert p.action == "none" and p.reason == "insufficient_depth"


def test_stop_loss_exit():
    e = engine()
    long_pos = PositionView(shares=400, avg_entry=0.50, marked_pnl=-50.0, entry_ts=NOW)
    p = e.evaluate(gs(), book(mid=0.49), fv(0.60), long_pos, NOW)
    assert p.action == "exit" and p.reason == "stop_loss"


def test_max_hold_exit():
    e = engine()
    long_pos = PositionView(shares=400, avg_entry=0.50, marked_pnl=2.0,
                            entry_ts=NOW - timedelta(seconds=1000))
    p = e.evaluate(gs(), book(mid=0.52), fv(0.60), long_pos, NOW)
    assert p.action == "exit" and p.reason == "max_hold"
