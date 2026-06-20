"""Live terminal dashboard for Optimiser."""

from __future__ import annotations

import threading
import time
from typing import Any

import httpx
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _fetch_stats(port: int) -> dict[str, Any] | None:
    try:
        r = httpx.get(f"http://127.0.0.1:{port}/stats", timeout=2.0)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _bar(ratio: float, width: int = 10) -> str:
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _make_savings_panel(stats: dict[str, Any]) -> Panel:
    attempted = stats.get("attempted_input_tokens_total", 0)
    saved = stats.get("tokens_saved_total", 0)
    after = attempted - saved if attempted else 0
    pct = (saved / attempted * 100) if attempted > 0 else 0
    cost_saved = saved / 1_000_000 * 3.0  # Claude Sonnet ~$3/MTok

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column(style="dim", min_width=22)
    t.add_column(style="bold", min_width=18)

    t.add_row("Tokens attempted", f"{attempted:,}")
    t.add_row("Tokens saved", f"[bold green]{saved:,}[/bold green]")
    t.add_row("Tokens sent", f"{after:,}")
    t.add_row(
        "Compression ratio",
        f"[bold {'green' if pct > 30 else 'yellow'}]{pct:.1f}%[/bold {'green' if pct > 30 else 'yellow'}]",
    )
    t.add_row("Est. cost saved", f"[bold yellow]${cost_saved:.4f}[/bold yellow]")

    requests = stats.get("requests_total", 0)
    cached = stats.get("requests_cached", 0)
    t.add_row("Requests proxied", f"{requests:,}")
    t.add_row("Cache hits", f"{cached:,}")

    return Panel(t, title="[bold green]TOKEN SAVINGS[/bold green]", border_style="green")


def _make_compressor_panel(stats: dict[str, Any]) -> Panel:
    breakdown = stats.get("compressor_breakdown", {})

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column(style="dim", min_width=16)
    t.add_column(min_width=24)

    if not breakdown:
        t.add_row("No data yet", "[dim]waiting for requests...[/dim]")
    else:
        for name, data in breakdown.items():
            ratio = float(data.get("avg_ratio_pct", data.get("avg_ratio", 0)))
            bar = _bar(ratio / 100)
            color = "green" if ratio > 50 else "yellow" if ratio > 25 else "white"
            t.add_row(name, f"[{color}]{bar}[/{color}] [bold]{ratio:.0f}%[/bold]")

    return Panel(t, title="[bold cyan]COMPRESSORS[/bold cyan]", border_style="cyan")


def _make_memory_panel(stats: dict[str, Any]) -> Panel:
    mem = stats.get("memory", {})

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    t.add_column(style="dim", min_width=22)
    t.add_column(style="bold", min_width=14)

    enabled = mem.get("enabled", False)
    if not enabled:
        t.add_row("Status", "[dim]disabled[/dim]")
        t.add_row("Enable with", "[dim]OPTIMISER_MEMORY=1[/dim]")
    else:
        t.add_row("Status", "[green]active[/green]")
        t.add_row("Memories stored", str(mem.get("total", 0)))
        t.add_row("Injected (session)", str(mem.get("injected_session", 0)))
        avg_score = mem.get("avg_relevance_score", 0)
        t.add_row("Avg relevance", f"{avg_score:.2f}")
        t.add_row("Backend", mem.get("backend", "sqlite"))

    return Panel(t, title="[bold yellow]MEMORY[/bold yellow]", border_style="yellow")


def _make_status_row(port: int, uptime_s: float) -> Text:
    mins = int(uptime_s // 60)
    secs = int(uptime_s % 60)
    uptime_str = f"{mins}m {secs:02d}s" if mins else f"{secs}s"
    t = Text()
    t.append("  Proxy: ", style="dim")
    t.append(f"http://127.0.0.1:{port}", style="bold cyan")
    t.append("   Uptime: ", style="dim")
    t.append(uptime_str, style="white")
    t.append("   ANTHROPIC_BASE_URL=http://127.0.0.1:", style="dim")
    t.append(str(port), style="dim")
    t.append("  claude", style="dim")
    return t


def _make_dashboard(stats: dict[str, Any] | None, port: int, uptime_s: float) -> Layout:
    layout = Layout()

    if stats is None:
        layout.update(
            Panel(
                "[yellow]Waiting for proxy to start...[/yellow]",
                title="[bold white]OPTIMISER v1.0[/bold white]",
                border_style="bold blue",
                subtitle="[dim]Ctrl+C to stop[/dim]",
            )
        )
        return layout

    status_row = _make_status_row(port, uptime_s)
    columns = Columns(
        [
            _make_savings_panel(stats),
            _make_compressor_panel(stats),
            _make_memory_panel(stats),
        ],
        equal=False,
        expand=True,
    )

    layout.update(
        Panel(
            Layout(
                Panel(status_row, border_style="dim", padding=(0, 1)),
                name="status",
            ),
            title="[bold white]  OPTIMISER v1.0  —  LIVE  [/bold white]",
            border_style="bold blue",
            subtitle="[dim]Ctrl+C to stop  |  curl localhost:{}/stats for full JSON[/dim]".format(port),
        )
    )

    # Rebuild with both status + columns
    inner = Layout()
    inner.split_column(
        Layout(Panel(status_row, border_style="dim", padding=(0, 0)), size=3),
        Layout(columns),
    )
    layout.update(
        Panel(
            inner,
            title="[bold white]  OPTIMISER v1.0  —  LIVE  [/bold white]",
            border_style="bold blue",
            subtitle="[dim]Ctrl+C to stop  ·  curl localhost:{}/stats  ·  ANTHROPIC_BASE_URL=http://127.0.0.1:{} claude[/dim]".format(
                port, port
            ),
        )
    )
    return layout


def run_dashboard(port: int, stop_event: threading.Event) -> None:
    """Render live dashboard until stop_event is set or Ctrl+C."""
    console = Console()
    start_time = time.monotonic()

    with Live(
        _make_dashboard(None, port, 0),
        refresh_per_second=2,
        console=console,
        screen=False,
    ) as live:
        try:
            while not stop_event.is_set():
                stats = _fetch_stats(port)
                uptime_s = time.monotonic() - start_time
                live.update(_make_dashboard(stats, port, uptime_s))
                time.sleep(0.5)
        except KeyboardInterrupt:
            stop_event.set()
