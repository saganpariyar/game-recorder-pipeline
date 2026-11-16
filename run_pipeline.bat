@echo off
title Game Recorder & YouTube Uploader Pipeline
echo ======================================================================
echo       Game Automation Pipeline - Record & Upload to YouTube
echo ======================================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv.
    echo Please make sure dependencies are installed.
    pause
    exit /b 1
)

echo Available options:
echo   1. Run Bikkad Web Pipeline (Playwright Video Recording + YouTube)
echo   2. Run Bikkad with OBS Studio WebSocket Recording
echo   3. Test Pipeline in Dry-Run Mode (Mock)
echo   4. Record Only (No YouTube upload)
echo   5. Test OBS WebSocket Connection
echo   6. Test YouTube OAuth Authentication
echo.
set /p choice="Enter choice [1-6] (default: 1): "
if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    echo Launching Bikkad Web Pipeline...
    ".venv\Scripts\python.exe" main.py --config config/bikkad_web.yaml
) else if "%choice%"=="2" (
    echo Launching Bikkad with OBS Recorder...
    ".venv\Scripts\python.exe" main.py --config config/bikkad_emulator.yaml
) else if "%choice%"=="3" (
    echo Running Dry-Run Simulation...
    ".venv\Scripts\python.exe" main.py --config config/bikkad_web.yaml --dry-run
) else if "%choice%"=="4" (
    echo Recording gameplay only (no upload)...
    ".venv\Scripts\python.exe" main.py --config config/bikkad_web.yaml --record-only
) else if "%choice%"=="5" (
    echo Testing OBS WebSocket connection...
    ".venv\Scripts\python.exe" main.py --test-obs
) else if "%choice%"=="6" (
    echo Testing YouTube OAuth Authentication...
    ".venv\Scripts\python.exe" main.py --test-youtube
) else (
    echo Invalid choice.
)

echo.
pause

