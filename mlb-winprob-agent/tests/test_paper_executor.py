import pytest

from agent.config import ExecutionCfg
from agent.models import BookState, Order
from agent.execution.paper import PaperExecutor


def mkbook(bids=None, asks=None):
    bids = bids or {}
    asks = asks or {}
    best_bid = max(bids) if bids else None
    best_ask = min(asks) if asks else None
    return BookState(market_id="m", best_bid=best_bid, best_ask=best_ask,
                     bid_depth=bids, ask_depth=asks)


def ex(slip=0.0, fee=0.0, maker=False):
    return PaperExecutor(ExecutionCfg(extra_slippage_cents=slip, taker_fee=fee, maker_mode=maker))


def test_walk_book_multiple_levels():
    e = ex()
    e.update_market(mkbook(asks={0.50: 100, 0.51: 100, 0.52: 100}))
    fills = e.submit(Order(side="buy", size=250))
    assert [f.size for f in fills] == [100, 100, 50]
    assert [f.price for f in fills] == [0.50, 0.51, 0.52]
    assert e.position() == 250
    assert e.avg_entry == pytest.approx((100 * 0.50 + 100 * 0.51 + 50 * 0.52) / 250)


def test_partial_reject_beyond_depth():
    e = ex()
    e.update_market(mkbook(asks={0.50: 200, 0.51: 100}))
    fills = e.submit(Order(side="buy", size=400))
    assert sum(f.size for f in fills) == 300  # 100 rejected
    assert e.position() == 300


def test_slippage_applied_both_sides():
    e = ex(slip=0.01)
    e.update_market(mkbook(asks={0.50: 100}))
    fills = e.submit(Order(side="buy", size=100))
    assert fills[0].price == pytest.approx(0.51)  # paid up
    e2 = ex(slip=0.01)
    e2.update_market(mkbook(bids={0.50: 100}))
    fills2 = e2.submit(Order(side="sell", size=100))
    assert fills2[0].price == pytest.approx(0.49)  # received less


def test_fee_applied():
    e = ex(fee=0.02)
    e.update_market(mkbook(asks={0.50: 100}))
    e.submit(Order(side="buy", size=100))
    # fee = 0.02 * 0.50 * 100 = 1.0, charged to realized
    assert e.pnl()["realized"] == pytest.approx(-1.0)


def test_realized_pnl_on_close():
    e = ex()
    e.update_market(mkbook(asks={0.50: 100}))
    e.submit(Order(side="buy", size=100))
    e.update_market(mkbook(bids={0.60: 100}))
    e.submit(Order(side="sell", size=100))
    assert e.position() == 0
    assert e.pnl()["realized"] == pytest.approx(10.0)  # (0.60-0.50)*100


def test_marked_pnl_long():
    e = ex()
    e.update_market(mkbook(asks={0.50: 100}))
    e.submit(Order(side="buy", size=100))
    e.update_market(mkbook(bids={0.59: 100}, asks={0.61: 100}))  # mid 0.60
    assert e.pnl()["marked"] == pytest.approx(10.0)


def test_short_then_cover_pnl():
    e = ex()
    e.update_market(mkbook(bids={0.60: 100}))
    e.submit(Order(side="sell", size=100))   # open short at 0.60
    assert e.position() == -100
    e.update_market(mkbook(asks={0.50: 100}))
    e.submit(Order(side="buy", size=100))    # cover at 0.50
    assert e.position() == 0
    assert e.pnl()["realized"] == pytest.approx(10.0)  # (0.60-0.50)*100 profit on short


def test_maker_order_rests_then_fills():
    e = ex(maker=True)
    e.update_market(mkbook(bids={0.49: 100}, asks={0.55: 100}))
    fills = e.submit(Order(side="buy", size=100, limit_price=0.50))
    assert fills == [] and e.position() == 0       # rests, ask 0.55 > 0.50
    e.update_market(mkbook(bids={0.49: 100}, asks={0.50: 100}))  # ask crosses
    assert e.position() == 100


def test_no_book_no_fill():
    e = ex()
    assert e.submit(Order(side="buy", size=100)) == []
