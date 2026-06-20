@echo off
setlocal EnableDelayedExpansion
title OPTIMISER Installer
color 0B

echo.
echo  ================================================================
echo    OPTIMISER v1.0  --  AI Token Saver
echo    Compress LLM context by 55-80%  *  One-click Windows install
echo  ================================================================
echo.

:: ─── Detect project dir (bat lives at repo root) ──────────────────
set "REPO_DIR=%~dp0"
if "%REPO_DIR:~-1%"=="\" set "REPO_DIR=%REPO_DIR:~0,-1%"

:: ─── Step 1: Python ───────────────────────────────────────────────
echo [1/7] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo       Python not found. Installing Python 3.12 via winget...
    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo  [ERROR] Python install failed. Visit https://python.org and install Python 3.12 manually.
        pause & exit /b 1
    )
    :: Refresh path
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo       Found: %%v

:: ─── Step 2: Rust ─────────────────────────────────────────────────
echo.
echo [2/7] Checking Rust toolchain...
set "CARGO_BIN=%USERPROFILE%\.cargo\bin"
set "PATH=%CARGO_BIN%;%PATH%"
cargo --version >nul 2>&1
if %errorlevel% neq 0 (
    echo       Rust not found. Installing via winget...
    winget install --id Rustlang.Rustup -e --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo  [ERROR] Rust install failed. Visit https://rustup.rs manually.
        pause & exit /b 1
    )
    set "PATH=%CARGO_BIN%;%PATH%"
)
for /f "tokens=*" %%v in ('cargo --version 2^>^&1') do echo       Found: %%v

:: ─── Step 3: VS Build Tools (MSVC linker) ─────────────────────────
echo.
echo [3/7] Checking MSVC C++ build tools...
set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%VCVARS%" (
    echo       VS Build Tools not found. Installing C++ toolchain ^(~1.5 GB^)...
    echo       This may take 5-15 minutes depending on your connection.
    winget install --id Microsoft.VisualStudio.2022.BuildTools -e ^
        --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended" ^
        --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo  [ERROR] VS Build Tools install failed.
        echo         Visit: https://aka.ms/vs/17/release/vs_BuildTools.exe
        pause & exit /b 1
    )
)
echo       Found MSVC build tools.

:: ─── Step 4: Activate MSVC environment ───────────────────────────
echo.
echo [4/7] Activating MSVC build environment...
call "%VCVARS%" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Could not activate MSVC environment.
    pause & exit /b 1
)
set "PATH=%CARGO_BIN%;%PATH%"
echo       MSVC environment ready.

:: ─── Step 5: Install Optimiser ────────────────────────────────────
echo.
echo [5/7] Installing Optimiser from source ^(compiling Rust extension^)...
echo       This takes 3-10 minutes on first install. Please wait...
echo.

cd /d "%REPO_DIR%"
pip install -e ".[proxy,mcp,code]" 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Optimiser install failed.
    echo         Check the output above for details.
    echo         Common fix: ensure you have internet access and try again.
    pause & exit /b 1
)
echo.
echo       Optimiser installed successfully.

:: ─── Step 6: Create desktop shortcut ─────────────────────────────
echo.
echo [6/7] Creating desktop shortcut...
set "SHORTCUT=%USERPROFILE%\Desktop\Start Optimiser.bat"
(
    echo @echo off
    echo title OPTIMISER
    echo color 0B
    echo set "PATH=%CARGO_BIN%;%PATH%"
    echo set "ANTHROPIC_BASE_URL=http://127.0.0.1:8787"
    echo echo.
    echo echo  Starting Optimiser...
    echo echo  Claude Code will use: ANTHROPIC_BASE_URL=http://127.0.0.1:8787
    echo echo.
    echo optimiser start
    echo pause
) > "%SHORTCUT%"
echo       Shortcut created: %SHORTCUT%

:: ─── Step 7: Set env vars permanently ────────────────────────────
echo.
echo [7/7] Setting ANTHROPIC_BASE_URL in your user environment...
setx ANTHROPIC_BASE_URL "http://127.0.0.1:8787" >nul
setx OPTIMISER_MEMORY "1" >nul
setx OPTIMISER_CODE_AWARE_ENABLED "1" >nul
echo       Environment variables set.

:: ─── Done ─────────────────────────────────────────────────────────
echo.
echo  ================================================================
echo    INSTALL COMPLETE!
echo  ================================================================
echo.
echo  HOW TO USE:
echo.
echo    1. Double-click "Start Optimiser" on your Desktop
echo       ^(or run: optimiser start^)
echo.
echo    2. Then use Claude Code normally:
echo       claude
echo       ^(ANTHROPIC_BASE_URL is already set in your environment^)
echo.
echo    3. Watch the live dashboard for token savings in real time.
echo.
echo  CHECK SAVINGS:
echo    curl http://127.0.0.1:8787/stats
echo.
echo  TO INTEGRATE WITH YOUR C# APPS (Hanomi, Bifrost):
echo    Change base URL in your Anthropic client to:
echo    http://127.0.0.1:8787
echo.
pause
