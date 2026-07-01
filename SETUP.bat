@echo off
setlocal EnableDelayedExpansion
title Optimiser Setup

echo.
echo  ==========================================
echo   OPTIMISER - One-Click Setup
echo   Local token saver for Claude Code
echo  ==========================================
echo.

cd /d "%~dp0"

:: ── STEP 1: Python check ─────────────────────────────────────────
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python not found.
    echo  Install Python 3.10+ from https://python.org then re-run this.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo  Found: %%v

:: ── STEP 2: Install package from local source ────────────────────
echo.
echo [2/4] Installing Optimiser from local source...
echo  (no PyPI, no external servers — only this folder)
echo.
pip install -e ".[proxy,mcp,code]" -q
if errorlevel 1 (
    echo.
    echo  ERROR: pip install failed. Check output above.
    pause
    exit /b 1
)
echo  Installed OK.

:: ── STEP 3: Register MCP tools with Claude Code ──────────────────
echo.
echo [3/4] Registering MCP tools with Claude Code...
optimiser mcp install
if errorlevel 1 (
    echo  Warning: MCP install had issues ^(Claude Code may not be installed yet^)
    echo  You can run   optimiser mcp install   later after installing Claude Code.
) else (
    echo  MCP tools registered.
)

:: ── STEP 4: Add to PATH so "oi" works everywhere ─────────────────
echo.
echo [4/4] Adding to PATH...
set "OI_DIR=%~dp0"
set "OI_DIR=%OI_DIR:~0,-1%"

:: Read current user PATH
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "CURPATH=%%b"

echo !CURPATH! | findstr /I /C:"%OI_DIR%" >nul 2>&1
if errorlevel 1 (
    reg add "HKCU\Environment" /v PATH /t REG_EXPAND_SZ /d "!CURPATH!;%OI_DIR%" /f >nul
    echo  Added: %OI_DIR%
) else (
    echo  Already in PATH.
)

:: ── DONE ─────────────────────────────────────────────────────────
echo.
echo  ==========================================
echo   Setup complete!
echo.
echo   HOW TO USE:
echo   Open any terminal and type:
echo.
echo      oi
echo.
echo   That starts the proxy + Claude Code.
echo   Close Claude to shut everything down.
echo.
echo   NOTE: Open a new terminal for "oi" to
echo   work (PATH needs a fresh shell).
echo  ==========================================
echo.
pause
