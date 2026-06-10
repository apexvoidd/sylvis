@echo off
title JARVIS System Assistant Launcher
color 0B
echo ===================================================
echo               INITIALIZING JARVIS OS               
echo ===================================================
echo.
echo [System Check] Checking Python 3.11 installation...
py -3.11 -c "import sys" >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.11 is not installed or not in PATH.
    echo Please ensure Python 3.11 is installed.
    pause
    exit /b 1
)

echo [System Check] Python 3.11 detected.
echo [System Check] Installing dependencies from requirements.txt...
py -3.11 -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [WARN] Pip installation had issues. Retrying normal installation...
    py -3.11 -m pip install -r requirements.txt
)

echo.
if exist "%USERPROFILE%\.fcc\custom_cabundle.pem" (
    set "SSL_CERT_FILE=%USERPROFILE%\.fcc\custom_cabundle.pem"
)

py -3.11 app.py
pause
