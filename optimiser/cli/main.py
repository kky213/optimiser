"""Main CLI entry point for Optimiser."""

import click

CLI_CONTEXT_SETTINGS = {"help_option_names": ["--help", "-?"]}


def get_version() -> str:
    """Get the current version."""
    try:
        from optimiser._version import __version__

        return __version__
    except ImportError:
        return "1.0.0"


@click.group(context_settings=CLI_CONTEXT_SETTINGS)
@click.version_option(get_version(), "--version", "-v", prog_name="optimiser")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Optimiser - AI Token Saver. Compress LLM context by 55-80%.

    Runs a local proxy that compresses everything going to your LLM,
    shapes output to be concise, and remembers context across sessions.

    \b
    Examples:
        optimiser start             Start proxy with live dashboard
        optimiser proxy             Start proxy (no dashboard)
        optimiser memory list       List stored memories
        optimiser stats             Show token savings summary
        optimiser wrap claude       Launch Claude Code through Optimiser
    """
    ctx.ensure_object(dict)

    # Fire a rate-limited, opt-out background check for newer releases so other
    # surfaces (e.g. the proxy banner) can show an "update available" notice.
    # Never blocks, never raises; skipped for `update` (it checks explicitly).
    if ctx.invoked_subcommand != "update":
        try:
            from optimiser.update_check import maybe_check_async

            maybe_check_async()
        except Exception:  # noqa: BLE001 — update check must never break the CLI
            pass


# Import subcommands - these register themselves with the main group
def _register_commands() -> None:
    """Register all subcommand groups."""
    from . import (
        agent_savings,  # noqa: F401
        audit,  # noqa: F401
        capture,  # noqa: F401
        copilot_auth,  # noqa: F401
        doctor,  # noqa: F401
        evals,  # noqa: F401
        init,  # noqa: F401
        install,  # noqa: F401
        learn,  # noqa: F401
        mcp,  # noqa: F401
        output_savings,  # noqa: F401
        perf,  # noqa: F401
        proxy,  # noqa: F401
        start,  # noqa: F401
        tools,  # noqa: F401
        update,  # noqa: F401
        wrap,  # noqa: F401
    )

    # Memory CLI requires numpy/hnswlib — optional
    try:
        from . import memory  # noqa: F401
    except ImportError:
        pass


_register_commands()


def _apply_help_aliases(command: click.Command) -> None:
    """Ensure `-?` works everywhere in the Click command tree."""
    context_settings = dict(command.context_settings or {})
    help_option_names = list(context_settings.get("help_option_names", []))
    if "--help" not in help_option_names:
        help_option_names.append("--help")
    if "-?" not in help_option_names:
        help_option_names.append("-?")
    context_settings["help_option_names"] = help_option_names
    command.context_settings = context_settings

    if isinstance(command, click.Group):
        for child in command.commands.values():
            _apply_help_aliases(child)


_apply_help_aliases(main)

if __name__ == "__main__":
    main()
