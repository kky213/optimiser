@echo off
echo Starting Claude Code through Optimiser proxy...
echo (Make sure start_optimiser.bat is running in another terminal first)
echo.

set ANTHROPIC_BASE_URL=http://127.0.0.1:8787
set HEADROOM_TELEMETRY=off
set HEADROOM_UPDATE_CHECK=off

claude
