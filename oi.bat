@echo off
:: Optimiser + Claude Code — single command launcher
:: Usage: oi
:: Starts proxy in background, launches Claude, kills proxy on exit.

set HEADROOM_TELEMETRY=off
set HEADROOM_TELEMETRY_WARN=off
set HEADROOM_UPDATE_CHECK=off
set HF_HUB_OFFLINE=1
set ANTHROPIC_BASE_URL=http://127.0.0.1:8787

:: Start proxy in background (hidden window)
start /B "" optimiser proxy --port 8787 > "%TEMP%\optimiser_proxy.log" 2>&1

:: Wait for proxy to be ready (up to 10 seconds)
echo Starting Optimiser proxy...
set /a tries=0
:waitloop
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:8787/health >nul 2>&1
if %errorlevel%==0 goto ready
set /a tries+=1
if %tries% lss 10 goto waitloop
echo Proxy slow to start — launching Claude anyway...
goto launch

:ready
echo Proxy ready. Token saving active.

:launch
echo.
:: Launch Claude Code (blocks until you exit)
claude

:: Claude exited — kill the proxy
echo.
echo Shutting down proxy...
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":8787 "') do taskkill /PID %%p /F >nul 2>&1
echo Done.
