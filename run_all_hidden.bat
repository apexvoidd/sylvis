@echo off
set "ANTHROPIC_AUTH_TOKEN=freecc"
cd /d "%~dp0"

:: Check Python 3.11 installation
py -3.11 -c "import sys" >nul 2>nul
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $ws.Popup('Python 3.11 is not installed! Please install Python 3.11 (and ensure it is added to your PATH) to run S.Y.L.V.I.S.', 0, 'S.Y.L.V.I.S. Launch Error', 16)"
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist ".venv" (
    py -3.11 -m venv .venv >nul 2>nul
    if not exist ".venv\Scripts\python.exe" (
        powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $ws.Popup('Failed to create the isolated virtual environment (.venv) in the project folder. Please ensure you have write permissions.', 0, 'S.Y.L.V.I.S. Launch Error', 16)"
        exit /b 1
    )
)

:: Set python command to the virtual environment
set "PYTHON_CMD=.venv\Scripts\python"

:: Check and install requirements
%PYTHON_CMD% -c "import flask, flask_cors, psutil, pycaw, comtypes, transformers, huggingface_hub, requests, webview, keyboard" >nul 2>nul
if %errorlevel% neq 0 (
    %PYTHON_CMD% -m pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        %PYTHON_CMD% -m pip install -r requirements.txt
        if %errorlevel% neq 0 (
            powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $ws.Popup('Failed to install Python dependencies from requirements.txt. Please check your internet connection.', 0, 'S.Y.L.V.I.S. Launch Error', 16)"
            exit /b 1
        )
    )
)

:: Set up environment variables for SSL certificate validation bypass
if exist "%USERPROFILE%\.fcc\custom_cabundle.pem" (
    set "SSL_CERT_FILE=%USERPROFILE%\.fcc\custom_cabundle.pem"
    set "REQUESTS_CA_BUNDLE=%USERPROFILE%\.fcc\custom_cabundle.pem"
    set "CURL_CA_BUNDLE=%USERPROFILE%\.fcc\custom_cabundle.pem"
    set "NODE_EXTRA_CA_CERTS=%USERPROFILE%\.fcc\custom_cabundle.pem"
)
if exist "%USERPROFILE%\.fcc\python_patch" (
    set "PYTHONPATH=%USERPROFILE%\.fcc\python_patch"
)

:: Terminate any existing processes on ports 5000 (app.py) and 8082 (fcc-server) to prevent conflicts
powershell -NoProfile -Command "Stop-Process -Id ((Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique) -Force -ErrorAction SilentlyContinue"
powershell -NoProfile -Command "Stop-Process -Id ((Get-NetTCPConnection -LocalPort 8082 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique) -Force -ErrorAction SilentlyContinue"

:: Wait for the OS to release the port sockets
ping -n 3 127.0.0.1 >nul

:: Start fcc-server silently in background of this hidden script (prefer local bundled, then user local bin, then global PATH)
if exist "%~dp0bin\fcc-server.exe" (
    start /b "" "%~dp0bin\fcc-server.exe"
) else if exist "%USERPROFILE%\.local\bin\fcc-server.exe" (
    start /b "" "%USERPROFILE%\.local\bin\fcc-server.exe"
) else (
    start /b "" fcc-server
)

:: Wait a brief moment (approx. 3 seconds) for fcc-server to initialize
ping -n 4 127.0.0.1 >nul

:: Start the Flask backend server
%PYTHON_CMD% app.py
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $ws.Popup('S.Y.L.V.I.S. terminated unexpectedly (Exit Code: ' + %errorlevel% + '). Please run run.bat in the project folder to see error details.', 0, 'S.Y.L.V.I.S. Crash Alert', 16)"
    exit /b %errorlevel%
)
