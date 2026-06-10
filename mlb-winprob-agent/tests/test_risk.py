from datetime import timedelta
from typing import Optional

from agent.clock import utcnow
from agent.config import RiskCfg
from agent.models import BookState, FairValue, GameState, Order
from agent.risk.gate import RiskGate

NOW = utcnow()


class FakeExecutor:
    def __init__(self, pos=0.0, total=0.0):
        self._pos = pos
        self._total = total

    def position(self):
        return self._pos

    @property
    def avg_entry(self):
        return 0.5

    def pnl(self):
        return {"realized": self._total, "marked": 0.0, "total": self._total}

    def submit(self, order):
        return []

    def cancel_all(self):
        pass

    def update_market(self, book):
        pass


def gs(status="live", age=0.0, changed=False):
    return GameState(game_pk=1, inning=5, half="top", outs=1, base_state=0,
                     home_score=2, away_score=2, status=status,
                     ingested_at=NOW - timedelta(seconds=age), state_changed=changed)


def book(mid=0.50, age=0.0):
    return BookState(market_id="m", best_bid=mid - 0.01, best_ask=mid + 0.01,
                     bid_depth={mid - 0.01: 1000}, ask_depth={mid + 0.01: 1000},
                     last_update=NOW - timedelta(seconds=age), staleness_limit=10.0)


def fv(p=0.6):
    return FairValue(prob=p, effective_n=1000, state_we=p, pregame_prior=0.5, blend_weight=1.0)


def gate(**kw):
    return RiskGate(RiskCfg(**kw), book_staleness=10.0, state_staleness=20.0)


def buy(size=400.0):
    return Order(side="buy", size=size)


def test_kill_switch_halts(tmp_path):
    kill = tmp_path / "KILL"
    kill.write_text("")
    g = gate(kill_file=str(kill))
    reason = g.heartbeat(gs(), book(), FakeExecutor(), NOW)
    assert reason == "kill_switch_file"
    assert g.halted


def test_fv_out_of_bounds_rejected():
    g = gate()
    r = g.check_order(buy(), fv(0.995), gs(), book(), FakeExecutor(), NOW)
    assert not r.approved and r.reason == "fv_out_of_bounds"


def test_fv_jump_without_state_change_rejected():
    g = gate(max_fv_jump=0.15)
    g.observe(fv(0.50))
    r = g.check_order(buy(), fv(0.80), gs(changed=False), book(), FakeExecutor(), NOW)
    assert not r.approved and r.reason == "fv_jump_no_state_change"


def test_fv_jump_allowed_with_state_change():
    g = gate(max_fv_jump=0.15)
    g.observe(fv(0.50))
    r = g.check_order(buy(), fv(0.80), gs(changed=True), book(), FakeExecutor(), NOW)
    assert r.approved


def test_order_rate_limit():
    g = gate(max_orders_per_minute=2)
    ex = FakeExecutor()
    assert g.check_order(buy(), fv(), gs(), book(), ex, NOW).approved
    assert g.check_order(buy(), fv(), gs(), book(), ex, NOW).approved
    r = g.check_order(buy(), fv(), gs(), book(), ex, NOW)
    assert not r.approved and r.reason == "order_rate_limit"


def test_position_share_cap_sizes_down():
    g = gate(max_position_shares=500, max_position_usd=10000, max_total_usd=10000)
    r = g.check_order(buy(1000), fv(), gs(), book(mid=0.50), FakeExecutor(), NOW)
    assert r.approved and r.size == 500 and r.reason == "approved_sized_down"


def test_position_usd_cap_sizes_down():
    g = gate(max_position_shares=100000, max_position_usd=100, max_total_usd=10000)
    r = g.check_order(buy(1000), fv(), gs(), book(mid=0.50), FakeExecutor(), NOW)
    assert r.approved and r.size == 200  # 100usd / 0.5


def test_total_capital_cap_sizes_down():
    g = gate(max_position_shares=100000, max_position_usd=100000, max_total_usd=50)
    r = g.check_order(buy(1000), fv(), gs(), book(mid=0.50), FakeExecutor(), NOW)
    assert r.approved and r.size == 100  # 50usd / 0.5


def test_limit_blocks_order_when_full():
    g = gate(max_position_shares=400)
    r = g.check_order(buy(400), fv(), gs(), book(), FakeExecutor(pos=400), NOW)
    assert not r.approved and r.reason == "limit_blocks_order"


def test_per_game_loss_limit_rejects_and_halts():
    g = gate(per_game_loss_limit=75)
    ex = FakeExecutor(total=-100)
    r = g.check_order(buy(), fv(), gs(), book(), ex, NOW)
    assert not r.approved and r.reason == "per_game_loss_limit"
    assert g.heartbeat(gs(), book(), ex, NOW) == "per_game_loss_limit"


def test_feed_disagreement_halts_after_window(tmp_path):
    g = gate(feed_disagreement_seconds=30, kill_file=str(tmp_path / "nokill"))
    ex = FakeExecutor()
    later = NOW + timedelta(seconds=31)
    # fresh book at each call so it stays "live"; game final but book live -> disagreement
    fresh_now = BookState(market_id="m", best_bid=0.49, best_ask=0.51,
                          bid_depth={0.49: 1000}, ask_depth={0.51: 1000},
                          last_update=NOW, staleness_limit=10.0)
    fresh_later = fresh_now.model_copy(update={"last_update": later})
    assert g.heartbeat(gs(status="final"), fresh_now, ex, NOW) is None  # starts timer
    assert g.heartbeat(gs(status="final"), fresh_later, ex, later) == "feed_disagreement"


def test_stale_book_feed_dead(tmp_path):
    g = gate(kill_file=str(tmp_path / "nokill"))
    # book age 35s > 3x staleness(10) -> dead
    assert g.heartbeat(gs(), book(age=35), FakeExecutor(), NOW) == "book_feed_dead"


def test_stale_game_feed_dead(tmp_path):
    g = gate(kill_file=str(tmp_path / "nokill"))
    # state age 65s > 3x state staleness(20) -> dead
    assert g.heartbeat(gs(age=65), book(), FakeExecutor(), NOW) == "game_feed_dead"
