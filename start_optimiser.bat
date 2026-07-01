@echo off
echo ============================================
echo   Optimiser Proxy - Local Only
echo   No telemetry. No phone-home. No PyPI.
echo ============================================
echo.
echo Proxy will run on http://127.0.0.1:8787
echo.
echo To use with Claude Code, open a second terminal and run:
echo   set ANTHROPIC_BASE_URL=http://127.0.0.1:8787
echo   claude
echo.
echo Press Ctrl+C to stop the proxy.
echo ============================================
echo.

set HEADROOM_TELEMETRY=off
set HEADROOM_TELEMETRY_WARN=off
set HEADROOM_UPDATE_CHECK=off
set HF_HUB_OFFLINE=1

cd /d "%~dp0"
optimiser proxy --port 8787
