# MLB Intra-Game Win-Probability Trading Agent

A **paper-trading** agent that ingests live MLB game state and a Polymarket
order book, computes a fair-value win probability from a win-expectancy table,
and trades the divergence between fair value and market price — with
conservative simulated fills and a risk gate that has final authority.

> **Paper trading is the product.** Live order placement is a stubbed interface
> behind a hard config gate. No wallet, no keys, no live orders in this build.

Operating principle: **latency is the enemy.** Every payload carries timestamps,
every decision checks data age, and the agent refuses to trade on stale data.
A correct system that refuses to trade on stale data is the success criterion.

---

## Quick start

```bash
pip install -r requirements.txt
python scripts/build_we_table.py          # writes data/we_table.csv
pytest -q                                  # 58 tests

# Synthetic end-to-end run (no network needed) -- dashboard + JSONL logging:
python run.py --mock --game 0 --market MOCK

# Replay a logged session at 10x:
python run.py --replay logs/<file>.jsonl --speed 10

# Post-game analysis (calibration, lead-lag, PnL, threshold sweep):
python scripts/analyze_log.py logs/*.jsonl

# Live (paper) against a real game -- requires network access (see findings):
python run.py --game <gamePk> --market <token_id>

# Kill switch: from another shell, mid-session:
touch ./KILL        # agent halts and flattens immediately
```

---

## Section 2 findings (external constraints — verified in this environment)

These were checked, not assumed. **This build environment uses an allowlist
network policy**: `pypi.org` and `github.com` are reachable, but general
internet egress is blocked at the proxy.

| Dependency | Result here | Notes |
|---|---|---|
| **MLB StatsAPI** (`statsapi.mlb.com`) | ❌ `HTTP 403` in ~0.05s | Blocked by the proxy, not geoblocking. No API key needed; the public `…/api/v1.1/game/{gamePk}/feed/live` feed is the correct endpoint and `mlb_feed.py` targets it. Parser is unit-tested against a sample payload. |
| **Polymarket international CLOB** (`clob.polymarket.com`) | ❌ `HTTP 403` | Also geoblocked for US IPs in general; `py-clob-client` would be needed off a non-US IP. |
| **Polymarket Gamma** (`gamma-api.polymarket.com`) | ❌ `HTTP 403` | Used to discover market/token IDs when reachable. |
| **US-regulated exchange (QCX LLC)** | n/a | Launched 2025–2026; no documented **public trading** API. Read-only book data is the realistic target. |

**Consequence, handled honestly (not silently mocked):** because the live
feeds are unreachable from here, the live clients (`mlb_feed.py`,
`clob_feed.py`) are implemented to the real API shapes so they work from an
unblocked IP, and a clearly-labeled `--mock` synthetic generator plus `--replay`
prove the *entire* stack end-to-end. All mock data is gated behind those flags.

**What I could not measure here** (needs an unblocked IP): real MLB market
spread/depth, single-game-market token-ID format, and StatsAPI update lag.
`clob_feed.py` REST polling + `analyze_log.py` lead-lag are the tools to measure
them once reachable; the expected procedure is documented inline.

---

## Architecture

```
StatsAPI  ─► mlb_feed ─┐
                       ├─► Agent.process_tick ─► Decision ─► logger (JSONL)
Polymarket ─► clob_feed┘        │                         └► dashboard (rich)
                                ▼
        estimator (WE table + pregame-prior blend) ─► FairValue
                                │
                signal.engine (FLAT→LONG|SHORT→FLAT, hysteresis,
                                cooldowns, no-trade windows, stale refusal)
                                │  proposes
                                ▼
                risk.gate (pre-trade checks + heartbeat; FINAL authority)
                                │  approves / sizes down / rejects / HALTS
                                ▼
                execution (paper: walks the book, slippage + fees | live: STUB)
```

The per-tick pipeline (`agent/core.py`) is shared by live, replay, and mock
modes, so replay exercises exactly the production decision path. `clock.py` is
the single source of time; replay drives a `ReplayClock` so all age/staleness
math behaves as it did live.

### Fair value
`data/we_table.csv` is keyed by `(inning, half, outs, base_state,
score_diff∈[-6,6])` with innings ≥10 collapsed to an "extras" bucket. Thin cells
(`n < min_cell_n`) are shrunk toward the n-weighted average of neighboring
score_diff cells. The state WE is blended with a manually-entered, de-vigged
pregame prior; the weight ramps from `blend_w_start` at inning 1 to 1.0 at
`blend_full_inning`.

> The shipped table is a **bootstrap, analytic** model (base-out run expectancy
> + a normal approximation of remaining run differential), **not** empirical
> Retrosheet data. Every value is synthetic and `n` is a plausibility estimate.
> The Retrosheet path (download → `cwevent` → aggregate) is documented in
> `scripts/build_we_table.py` and intentionally not run automatically.

---

## Phase 3 gate — live execution (NOT implemented)

`agent/execution/live_stub.py` implements the `Executor` interface but every
method raises `NotImplementedError`. **The run loop refuses to start if
`mode: live`** (the live executor is the stub). To go live in a future Phase 3
you would: (1) implement order signing/placement against the reachable exchange
API, (2) add wallet + key management (out of scope here), (3) replace the stub,
(4) keep the risk gate and kill switch in the critical path. None of that is in
this build by design.

---

## Configuration

All tunables live in `config.yaml`, validated by pydantic at startup
(`agent/config.py`). The loader **rejects unknown keys** and **refuses to run if
`entry_threshold <= exit_threshold`** (hysteresis is mandatory). Groups: `mode`,
`market`, `feeds`, `fairvalue`, `signal`, `execution`, `risk`.

---

## Risk controls

Pre-trade (reject/size-down): position-share, position-USD, total-capital,
per-game loss, daily loss, fair-value bounds, fair-value-jump-without-state-change
(bug guard), and order-rate limits. Heartbeat (cancel-all + flatten + HALT until
manually cleared): the `./KILL` file, feed disagreement (book live but game final
or vice versa > N s), and either feed stale beyond 3× its limit.

---

## On whether an exploitable edge exists

The honest read this project is built to deliver: run `analyze_log.py` over real
logged games and look at the **lead-lag** section. If the market *leads* our
state-derived fair value (negative peak lag), the apparent "edge" is just
latency — us catching up to a market that already moved — and the paper PnL is
not real. The tool says this loudly.

On the **synthetic** `--mock` data, the generator deliberately makes the market
**lag** fair value by 3 ticks (~9s), so the analysis reports "fv LEADS by +9s"
and the agent books a profit. **That is an artifact of the mock**, included to
prove the full pipeline (signal → risk → fills → PnL → analysis), **not**
evidence of real edge. A single mock game also makes the calibration buckets
degenerate (one outcome). Real conclusions require many real games — which need
an unblocked IP this environment does not provide.

---

## Tests

```bash
pytest -q
```

Coverage: config validation (unknown keys, hysteresis); WE lookup + shrinkage
(missing cells, extras bucket, score-diff cap, walk-off states); signal
hysteresis / cooldowns / no-trade windows / **every stale-data refusal path**;
every risk check incl. the kill-switch file; paper fill math (book walking,
partial rejects, slippage, fees, short cover, maker resting fills); StatsAPI and
CLOB parsers; and one **golden integration test** that replays a recorded
session through the full stack and asserts the decision log byte-for-byte, plus
a mid-replay kill-switch flatten test.

Regenerate the golden after intentional behavior changes:
`python tests/test_integration_replay.py --regen`.
