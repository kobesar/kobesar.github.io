"""Polymarket CLOB order-book feed -> BookState stream.

Primary path: the market websocket channel (snapshot 'book' message, then
'price_change' deltas), with a heartbeat watchdog + exponential-backoff
reconnect that re-requests a snapshot before trusting the book again.

Fallback path: REST polling of the /book endpoint. The international CLOB is
geoblocked for US IPs and the US (QCX) exchange has no documented public
trading API, so the REST read-only fallback is what actually runs in many
environments (see README section 2 findings). The book-building helpers are
pure functions so they are unit-tested without network.
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from ..clock import utcnow
from ..models import BookState

TOP_LEVELS = 5


def _levels_to_dict(levels: list[dict[str, Any]], reverse: bool) -> dict[float, float]:
    """Convert [{'price','size'}, ...] to a {price: size} dict of the top levels.
    reverse=True for bids (highest price first), False for asks (lowest first)."""
    parsed = []
    for lvl in levels:
        try:
            px = float(lvl["price"])
            sz = float(lvl["size"])
        except (KeyError, TypeError, ValueError):
            continue
        if sz <= 0:
            continue
        parsed.append((px, sz))
    parsed.sort(key=lambda x: x[0], reverse=reverse)
    return {px: sz for px, sz in parsed[:TOP_LEVELS]}


class BookBuilder:
    """Maintains a book from a snapshot plus incremental price_change deltas.

    `trusted` is False until a snapshot has been applied; after a reconnect the
    feed resets it so we don't act on a half-built book.
    """

    def __init__(self, market_id: str, staleness_limit: float = 10.0) -> None:
        self.market_id = market_id
        self.staleness_limit = staleness_limit
        self._bids: dict[float, float] = {}
        self._asks: dict[float, float] = {}
        self.trusted = False
        self._last_update = utcnow()

    def reset(self) -> None:
        self._bids.clear()
        self._asks.clear()
        self.trusted = False

    def apply_snapshot(self, bids: list[dict], asks: list[dict]) -> None:
        self._bids = {float(b["price"]): float(b["size"]) for b in bids if float(b["size"]) > 0}
        self._asks = {float(a["price"]): float(a["size"]) for a in asks if float(a["size"]) > 0}
        self.trusted = True
        self._last_update = utcnow()

    def apply_changes(self, changes: list[dict]) -> None:
        """Each change: {'side': 'buy'|'sell', 'price', 'size'}; size 0 removes."""
        for ch in changes:
            try:
                side = ch["side"].lower()
                px = float(ch["price"])
                sz = float(ch["size"])
            except (KeyError, TypeError, ValueError):
                continue
            book = self._bids if side in ("buy", "bid") else self._asks
            if sz <= 0:
                book.pop(px, None)
            else:
                book[px] = sz
        self._last_update = utcnow()

    def to_state(self) -> BookState:
        bid_dict = _levels_to_dict([{"price": p, "size": s} for p, s in self._bids.items()], reverse=True)
        ask_dict = _levels_to_dict([{"price": p, "size": s} for p, s in self._asks.items()], reverse=False)
        best_bid = max(bid_dict) if bid_dict else None
        best_ask = min(ask_dict) if ask_dict else None
        return BookState(
            market_id=self.market_id,
            best_bid=best_bid,
            best_ask=best_ask,
            bid_depth=bid_dict,
            ask_depth=ask_dict,
            last_update=self._last_update,
            staleness_limit=self.staleness_limit,
        )


def parse_ws_message(msg: dict[str, Any], builder: BookBuilder) -> bool:
    """Apply one websocket message to the builder. Returns True if the book
    changed. Handles 'book' (snapshot) and 'price_change' (delta)."""
    mtype = msg.get("event_type") or msg.get("type")
    if mtype == "book":
        builder.apply_snapshot(msg.get("bids", []), msg.get("asks", []))
        return True
    if mtype == "price_change":
        builder.apply_changes(msg.get("changes", []))
        return True
    return False


def parse_rest_book(payload: dict[str, Any], market_id: str, staleness_limit: float) -> BookState:
    """Parse a /book REST response ({'bids':[...], 'asks':[...]}) -> BookState."""
    bid_dict = _levels_to_dict(payload.get("bids", []), reverse=True)
    ask_dict = _levels_to_dict(payload.get("asks", []), reverse=False)
    return BookState(
        market_id=market_id,
        best_bid=max(bid_dict) if bid_dict else None,
        best_ask=min(ask_dict) if ask_dict else None,
        bid_depth=bid_dict,
        ask_depth=ask_dict,
        last_update=utcnow(),
        staleness_limit=staleness_limit,
    )


class ClobFeed:
    """Thread-safe holder of the latest BookState, fed by either the websocket
    runner or the REST poller. The run loop only calls `latest()`."""

    def __init__(self, token_id: str, market_id: str, ws_url: str, rest_url: str,
                 staleness_limit: float = 10.0, poll_seconds: float = 2.0) -> None:
        self.token_id = token_id
        self.market_id = market_id
        self.ws_url = ws_url
        self.rest_url = rest_url.rstrip("/")
        self.staleness_limit = staleness_limit
        self.poll_seconds = poll_seconds
        self._lock = threading.Lock()
        self._latest: Optional[BookState] = None
        self._builder = BookBuilder(market_id, staleness_limit)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def latest(self) -> Optional[BookState]:
        with self._lock:
            return self._latest

    def _set(self, state: BookState) -> None:
        with self._lock:
            self._latest = state

    # ----- REST fallback (thread) -----
    def _poll_once(self, client) -> None:
        try:
            resp = client.get(f"{self.rest_url}/book", params={"token_id": self.token_id}, timeout=10.0)
            resp.raise_for_status()
            self._set(parse_rest_book(resp.json(), self.market_id, self.staleness_limit))
        except Exception:
            pass  # keep last good; staleness is detected by age

    def start_rest_poll(self) -> None:
        import httpx

        def loop() -> None:
            with httpx.Client() as client:
                while not self._stop.is_set():
                    self._poll_once(client)
                    self._stop.wait(self.poll_seconds)

        self._thread = threading.Thread(target=loop, name="clob-rest", daemon=True)
        self._thread.start()

    # ----- websocket runner (async) -----
    async def run_ws(self) -> None:
        """Connect, subscribe, apply snapshot+deltas with watchdog + backoff.
        Re-requests a snapshot (reset builder) on every reconnect."""
        import asyncio
        import json

        import websockets

        backoff = 1.0
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.ws_url, open_timeout=10) as ws:
                    self._builder.reset()
                    await ws.send(json.dumps({"assets_ids": [self.token_id], "type": "market"}))
                    backoff = 1.0
                    while not self._stop.is_set():
                        raw = await asyncio.wait_for(ws.recv(), timeout=self.staleness_limit)
                        msg = json.loads(raw)
                        for m in (msg if isinstance(msg, list) else [msg]):
                            if parse_ws_message(m, self._builder) and self._builder.trusted:
                                self._set(self._builder.to_state())
            except Exception:
                # watchdog timeout / disconnect -> back off and reconnect (fresh snapshot)
                await asyncio.sleep(min(backoff, 30.0))
                backoff = min(backoff * 2.0, 30.0)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
