import pytest

from agent.ingest.clob_feed import BookBuilder, parse_rest_book, parse_ws_message
from agent.ingest.mlb_feed import parse_feed

SAMPLE_FEED = {
    "metaData": {"timeStamp": "20240601_011530"},
    "gameData": {"status": {"abstractGameState": "Live", "detailedState": "In Progress"}},
    "liveData": {"linescore": {
        "currentInning": 7, "inningHalf": "Bottom", "outs": 2,
        "teams": {"home": {"runs": 4}, "away": {"runs": 3}},
        "offense": {"first": {"id": 1}, "third": {"id": 2}},  # 1B and 3B occupied
    }},
}


def test_parse_feed_basic():
    gs = parse_feed(SAMPLE_FEED, game_pk=12345)
    assert gs.game_pk == 12345
    assert gs.inning == 7 and gs.half == "bottom" and gs.outs == 2
    assert gs.home_score == 4 and gs.away_score == 3
    assert gs.base_state == 1 | 4  # 1B + 3B = 5
    assert gs.status == "live"
    assert gs.source_ts is not None and gs.source_ts.year == 2024


def test_parse_feed_score_diff_capped():
    feed = {**SAMPLE_FEED}
    feed["liveData"] = {"linescore": {"currentInning": 3, "inningHalf": "Top", "outs": 0,
                                      "teams": {"home": {"runs": 12}, "away": {"runs": 1}},
                                      "offense": {}}}
    gs = parse_feed(feed, 1)
    assert gs.score_diff == 6  # capped


def test_parse_feed_status_mapping():
    for raw, expect in [("Preview", "scheduled"), ("Final", "final"), ("Live", "live")]:
        feed = {"gameData": {"status": {"abstractGameState": raw, "detailedState": raw}},
                "liveData": {"linescore": {}}, "metaData": {}}
        assert parse_feed(feed, 1).status == expect


def test_parse_feed_delayed():
    feed = {"gameData": {"status": {"abstractGameState": "Live", "detailedState": "Delayed: Rain"}},
            "liveData": {"linescore": {}}, "metaData": {}}
    assert parse_feed(feed, 1).status == "delayed"


def test_book_builder_snapshot_then_delta():
    b = BookBuilder("m", staleness_limit=10)
    assert not b.trusted
    msg = {"event_type": "book",
           "bids": [{"price": "0.60", "size": "1000"}, {"price": "0.59", "size": "500"}],
           "asks": [{"price": "0.62", "size": "800"}]}
    assert parse_ws_message(msg, b) and b.trusted
    st = b.to_state()
    assert st.best_bid == 0.60 and st.best_ask == 0.62
    # delta: remove the 0.62 ask, add a better one
    parse_ws_message({"event_type": "price_change",
                      "changes": [{"side": "sell", "price": "0.62", "size": "0"},
                                  {"side": "sell", "price": "0.61", "size": "300"}]}, b)
    assert b.to_state().best_ask == 0.61


def test_book_builder_reset_untrusts():
    b = BookBuilder("m")
    b.apply_snapshot([{"price": "0.5", "size": "10"}], [{"price": "0.6", "size": "10"}])
    assert b.trusted
    b.reset()
    assert not b.trusted and b.to_state().best_bid is None


def test_parse_rest_book():
    payload = {"bids": [{"price": "0.40", "size": "100"}, {"price": "0.41", "size": "200"}],
               "asks": [{"price": "0.45", "size": "150"}]}
    st = parse_rest_book(payload, "m", 10.0)
    assert st.best_bid == 0.41 and st.best_ask == 0.45
    assert st.spread == pytest.approx(0.04)
