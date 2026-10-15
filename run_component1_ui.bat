@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

set COMP1=%~dp0
echo ============================================================
echo   Component 1: Log Ingestion & Memory Failure Pipeline UI
echo   Root: %COMP1%
echo ============================================================
echo.

set VENV=%COMP1%venv311
if not exist "%VENV%\Scripts\python.exe" set "VENV=%COMP1%venv"

if not exist "%VENV%\Scripts\python.exe" (
    echo [INFO] Creating Python virtual environment for Component 1...
    python -m venv "%COMP1%venv311"
    set "VENV=%COMP1%venv311"
    echo [INFO] Installing requirements...
    "%VENV%\Scripts\python.exe" -m pip install -r "%COMP1%requirements.txt" --quiet
)

echo [INFO] Starting Component 1 Ingestion API & Process Explorer UI on port 8001...
start "COMP1 - Process Explorer :8001" cmd /k "cd /d "%COMP1%" && "%VENV%\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload"

echo [INFO] Waiting for server to initialize...
timeout /t 3 >nul

echo [INFO] Opening Component 1 UI in default browser...
start "" "http://localhost:8001/"

echo.
echo ============================================================
echo   Component 1 Process Explorer is live at:
echo   http://localhost:8001/
echo ============================================================
echo.
pause
