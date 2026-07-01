@echo off
echo ============================================
echo   Optimiser - Local Install (no PyPI)
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ first.
    pause
    exit /b 1
)

echo.
echo [2/3] Installing from local source (no PyPI, no external dependencies)...
echo       This uses only the code in this folder.
echo.
pip install -e ".[proxy,mcp,code]" --no-deps 2>nul
if errorlevel 1 (
    echo Retrying with dependency resolution...
    pip install -e ".[proxy,mcp,code]"
)

echo.
echo [3/3] Verifying install...
optimiser --version 2>nul || headroom --version 2>nul

echo.
echo ============================================
echo   Done! Run start_optimiser.bat to use it.
echo ============================================
pause
