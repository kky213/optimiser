"""optimiser start — launch proxy with live savings dashboard."""

from __future__ import annotations

import subprocess
import sys
import threading
import time

import click
import httpx

from optimiser.cli.main import main


@main.command("start")
@click.option("--port", "-p", default=8787, show_default=True, help="Proxy port.")
@click.option("--no-dashboard", is_flag=True, default=False, help="Skip live dashboard, just run proxy.")
@click.option("--no-memory", is_flag=True, default=False, help="Disable persistent memory.")
@click.option("--no-output-shaping", is_flag=True, default=False, help="Disable output verbosity shaping.")
def start(port: int, no_dashboard: bool, no_memory: bool, no_output_shaping: bool) -> None:
    """Start Optimiser proxy with live savings dashboard.

    \b
    Examples:
        optimiser start                    Start on port 8787 with dashboard
        optimiser start --port 9090        Custom port
        optimiser start --no-dashboard     Proxy only, no UI
        optimiser start --no-memory        Skip persistent memory

    Once running, point your LLM client here:
        ANTHROPIC_BASE_URL=http://127.0.0.1:8787 claude
    """
    import os

    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{port}"

    if no_memory:
        env["OPTIMISER_MEMORY"] = "0"
    if no_output_shaping:
        env["HEADROOM_OUTPUT_SHAPER"] = "0"

    # Build proxy sub-command args
    proxy_cmd = [sys.executable, "-m", "optimiser.proxy", "--port", str(port)]

    click.echo()
    click.echo("  ╔═══════════════════════════════════════════════════╗")
    click.echo("  ║          OPTIMISER v1.0  —  Starting...           ║")
    click.echo("  ║    AI Token Saver  ·  Compress LLM by 55-80%      ║")
    click.echo("  ╚═══════════════════════════════════════════════════╝")
    click.echo()
    click.echo(f"  Proxy port : {port}")
    click.echo(f"  Memory     : {'OFF' if no_memory else 'ON (project-scoped)'}")
    click.echo(f"  Output shaping: {'OFF' if no_output_shaping else 'ON'}")
    click.echo(f"  Code-aware : ON")
    click.echo()
    click.echo(f"  Use with Claude Code:")
    click.echo(f"    ANTHROPIC_BASE_URL=http://127.0.0.1:{port} claude")
    click.echo()

    # Start proxy using the installed headroom proxy command (already installed)
    proxy_cmd = [
        sys.executable, "-c",
        f"from optimiser.cli.proxy import proxy; proxy(standalone_mode=False)",
    ]

    # Simpler: just invoke optimiser proxy directly
    exe = "optimiser"
    proxy_args = [exe, "proxy", "--port", str(port)]

    try:
        proc = subprocess.Popen(
            proxy_args,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        # Fallback: use Python module invocation
        proxy_args = [sys.executable, "-m", "optimiser.cli", "proxy", "--port", str(port)]
        proc = subprocess.Popen(
            proxy_args,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

    # Wait for proxy to become healthy (up to 30s)
    click.echo("  Waiting for proxy to start", nl=False)
    for i in range(60):
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/livez", timeout=1.0)
            if r.status_code == 200:
                break
        except Exception:
            pass
        if proc.poll() is not None:
            # Proxy died — print output and exit
            click.echo()
            out = proc.stdout.read() if proc.stdout else ""
            click.echo(f"\n[ERROR] Proxy exited early:\n{out}", err=True)
            sys.exit(1)
        click.echo(".", nl=False)
        time.sleep(0.5)
    else:
        click.echo()
        click.echo("[WARNING] Proxy did not respond in 30s — starting dashboard anyway.")

    click.echo()
    click.echo(f"\n  [OK] Proxy running at http://127.0.0.1:{port}")
    click.echo()

    if no_dashboard:
        # Just block waiting for proxy
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
        return

    # Launch live dashboard in main thread; proxy runs in background
    stop_event = threading.Event()

    def _proxy_watcher() -> None:
        proc.wait()
        stop_event.set()

    watcher = threading.Thread(target=_proxy_watcher, daemon=True)
    watcher.start()

    try:
        from optimiser.dashboard.live import run_dashboard
        run_dashboard(port, stop_event)
    except ImportError:
        # Rich not available — just block
        click.echo("  (Install 'rich' for live dashboard: pip install rich)")
        try:
            proc.wait()
        except KeyboardInterrupt:
            pass
    except KeyboardInterrupt:
        pass
    finally:
        if proc.poll() is None:
            click.echo("\n  Stopping Optimiser proxy...")
            proc.terminate()
            proc.wait(timeout=5)
        click.echo("  Goodbye.")
