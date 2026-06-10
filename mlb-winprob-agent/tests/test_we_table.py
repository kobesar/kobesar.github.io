import pytest

from agent.fairvalue.we_table import Cell, WeTable


def make_table(cells, min_cell_n=200):
    return WeTable(cells, min_cell_n=min_cell_n)


def test_exact_lookup_no_shrink():
    cells = {(1, "top", 0, 0, 0): Cell(0.55, 5000)}
    t = make_table(cells)
    r = t.lookup(1, "top", 0, 0, 0)
    assert r.prob == 0.55
    assert r.effective_n == 5000
    assert r.raw == 0.55


def test_shrinkage_thin_cell():
    # thin cell n=50 between two strong neighbors at 0.30 and 0.70
    cells = {
        (1, "top", 0, 0, -1): Cell(0.30, 1000),
        (1, "top", 0, 0, 0): Cell(0.90, 50),     # implausible thin value
        (1, "top", 0, 0, 1): Cell(0.70, 1000),
    }
    t = make_table(cells, min_cell_n=200)
    r = t.lookup(1, "top", 0, 0, 0)
    neigh = (0.30 * 1000 + 0.70 * 1000) / 2000  # 0.50
    expected = (50 * 0.90 + 200 * neigh) / (50 + 200)
    assert r.prob == pytest.approx(expected)
    assert r.effective_n == pytest.approx(250)
    assert r.raw == 0.90  # raw preserved


def test_missing_cell_returns_neighbor_avg_n0():
    cells = {
        (1, "top", 0, 0, -1): Cell(0.40, 800),
        (1, "top", 0, 0, 1): Cell(0.60, 200),
    }
    t = make_table(cells)
    r = t.lookup(1, "top", 0, 0, 0)
    assert r.effective_n == 0.0
    assert r.prob == pytest.approx((0.40 * 800 + 0.60 * 200) / 1000)


def test_missing_cell_no_neighbors_is_coinflip():
    t = make_table({(5, "bottom", 1, 2, 3): Cell(0.5, 100)})
    r = t.lookup(1, "top", 0, 0, 0)
    assert r.prob == 0.5
    assert r.effective_n == 0.0


def test_extras_bucket_collapses():
    cells = {(10, "top", 0, 0, 0): Cell(0.5, 4000)}
    t = make_table(cells)
    # inning 12 should map to the extras bucket (10)
    r = t.lookup(12, "top", 0, 0, 0)
    assert r.prob == 0.5


def test_score_diff_capped():
    cells = {(9, "bottom", 2, 0, 6): Cell(0.99, 4000)}
    t = make_table(cells)
    # diff 9 caps to 6 -> walk-off-ish blowout lead
    r = t.lookup(9, "bottom", 2, 0, 9)
    assert r.prob == 0.99


def test_real_table_loads_and_is_monotone_in_score():
    t = WeTable.load("data/we_table.csv", min_cell_n=200)
    # more runs ahead -> higher home win prob, same state otherwise
    lo = t.lookup(5, "top", 1, 0, -2).prob
    mid = t.lookup(5, "top", 1, 0, 0).prob
    hi = t.lookup(5, "top", 1, 0, 2).prob
    assert lo < mid < hi


def test_real_table_walkoff_state():
    t = WeTable.load("data/we_table.csv", min_cell_n=200)
    # home leading in the bottom of the 9th should be a strong favorite
    r = t.lookup(9, "bottom", 2, 0, 1)
    assert r.prob > 0.8
