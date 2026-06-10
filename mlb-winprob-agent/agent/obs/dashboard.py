"""rich live dashboard: one refreshing panel per tick."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from ..config import Config
from ..models import Decision

_ARROW = {"top": "▲", "bottom": "▼"}  # ▲ ▼
_BASES = [(1, "1B"), (2, "2B"), (4, "3B")]


def _runners(base_state: int) -> str:
    names = [name for bit, name in _BASES if base_state & bit]
    return ",".join(names) if names else "empty"


def _fmt_size(book, px: Optional[float]) -> str:
    if px is None:
        return "--"
    size = book.bid_depth.get(px) or book.ask_depth.get(px)
    return f"x{int(size)}" if size else ""


def render(decision: Decision, cfg: Config, kill_present: bool,
           halt_reason: str, now: datetime) -> Panel:
    gs = decision.game_state
    book = decision.book
    fv = decision.fair_value

    inning_word = f"{gs.inning}" + ("th" if 10 <= gs.inning % 100 <= 13
                                    else {1: "st", 2: "nd", 3: "rd"}.get(gs.inning % 10, "th"))
    head = Text()
    head.append(f"GAME {inning_word} {_ARROW.get(gs.half, '?')} | {gs.outs} out | "
                f"runners {_runners(gs.base_state)} | "
                f"AWAY {gs.away_score} - {gs.home_score} HOME")
    head.append(f"      state age: {gs.state_age_seconds(now):.1f}s  [{gs.status}]")

    if fv is not None:
        fvl = Text(f"FAIR VALUE {fv.prob:.3f} (n={fv.effective_n:,.0f}, "
                   f"w={fv.blend_weight:.2f}, prior={fv.pregame_prior:.2f})", style="cyan")
    else:
        fvl = Text("FAIR VALUE  --", style="cyan")

    mid = book.mid
    mkt = Text(f"MARKET     bid {book.best_bid if book.best_bid is not None else '--'} "
               f"{_fmt_size(book, book.best_bid)} | "
               f"mid {mid:.3f} | " if mid is not None else "MARKET     -- | ")
    mkt.append(f"ask {book.best_ask if book.best_ask is not None else '--'} "
               f"{_fmt_size(book, book.best_ask)}   book age: {book.age_seconds(now):.1f}s")

    edge = decision.edge
    edge_l = Text(f"EDGE       {edge:+.3f}   threshold {cfg.signal.entry_threshold:.3f}"
                  if edge is not None else "EDGE       --")
    edge_l.append(f"                action: {decision.action.upper()} ({decision.reason})",
                  style="yellow")

    avg = f"@ {decision.avg_entry:.3f}" if decision.avg_entry is not None else ""
    pos = Text(f"POSITION   {decision.position:+.0f} {avg}   "
               f"marked PnL {decision.marked_pnl:+.2f}   realized {decision.realized_pnl:+.2f}")

    deployed = abs(decision.position) * (decision.avg_entry or 0.0)
    risk_line = Text(
        f"RISK       {'HALTED:' + halt_reason if halt_reason else 'OK'}   "
        f"deployed ${deployed:.0f}/${cfg.risk.max_total_usd:.0f}   "
        f"game loss ${max(0.0, -decision.realized_pnl - decision.marked_pnl):.0f}/"
        f"${cfg.risk.per_game_loss_limit:.0f}   "
        f"kill: {'PRESENT' if kill_present else 'not present'}",
        style="red" if (halt_reason or kill_present) else "green",
    )

    return Panel(Group(head, fvl, mkt, edge_l, pos, risk_line),
                 title=f"MLB win-prob agent [{cfg.mode}]", border_style="blue")


class Dashboard:
    def __init__(self, cfg: Config, enabled: bool = True) -> None:
        self.cfg = cfg
        self.enabled = enabled
        self._live: Optional[Live] = None

    def __enter__(self) -> "Dashboard":
        if self.enabled:
            self._live = Live(auto_refresh=False, screen=False)
            self._live.__enter__()
        return self

    def update(self, decision: Decision, kill_present: bool, halt_reason: str,
               now: datetime) -> None:
        if self._live is not None:
            self._live.update(render(decision, self.cfg, kill_present, halt_reason, now))
            self._live.refresh()

    def __exit__(self, *exc) -> None:
        if self._live is not None:
            self._live.__exit__(*exc)
