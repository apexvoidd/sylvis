@echo off
set "ANTHROPIC_AUTH_TOKEN=freecc"
title S.Y.L.V.I.S. Launcher
color 0B
echo ===================================================
echo               INITIALIZING S.Y.L.V.I.S. OS               
echo ===================================================
echo.
echo [System Check] Checking Python 3.11 installation...
py -3.11 -c "import sys" >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.11 is not installed or not in PATH.
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $ws.Popup('Python 3.11 is not installed! Please install Python 3.11 (and ensure it is added to your PATH) to run S.Y.L.V.I.S.', 0, 'S.Y.L.V.I.S. Launch Error', 16)"
    pause
    exit /b 1
)

echo [System Check] Python 3.11 detected.

:: Setup virtual environment
if not exist ".venv" (
    echo [System Check] Creating isolated virtual environment (.venv)...
    py -3.11 -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo [ERROR] Failed to create virtual environment.
        powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $ws.Popup('Failed to create the isolated virtual environment (.venv) in the project folder.', 0, 'S.Y.L.V.I.S. Launch Error', 16)"
        pause
        exit /b 1
    )
)

set "PYTHON_CMD=.venv\Scripts\python"

echo [System Check] Checking/Installing dependencies from requirements.txt...
%PYTHON_CMD% -c "import flask, flask_cors, psutil, pycaw, comtypes, transformers, huggingface_hub, requests, webview, keyboard, speech_recognition" >nul 2>nul
if %errorlevel% neq 0 (
    echo [System Check] Installing missing dependencies...
    %PYTHON_CMD% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $ws.Popup('Failed to install Python dependencies from requirements.txt.', 0, 'S.Y.L.V.I.S. Launch Error', 16)"
        pause
        exit /b 1
    )
) else (
    echo [System Check] All dependencies are already installed.
)

echo.
if exist "%USERPROFILE%\.fcc\custom_cabundle.pem" (
    set "SSL_CERT_FILE=%USERPROFILE%\.fcc\custom_cabundle.pem"
)

%PYTHON_CMD% app.py
if %errorlevel% neq 0 (
    echo.
    echo [CRITICAL] S.Y.L.V.I.S. exited with error code %errorlevel%.
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $ws.Popup('S.Y.L.V.I.S. terminated unexpectedly (Exit Code: ' + %errorlevel% + '). Check the console window for logs.', 0, 'S.Y.L.V.I.S. Crash Alert', 16)"
)
pause
