@echo off
cd /d "%~dp0"

:: Set up environment variables for SSL certificate validation bypass
set "SSL_CERT_FILE=%USERPROFILE%\.fcc\custom_cabundle.pem"
set "REQUESTS_CA_BUNDLE=%USERPROFILE%\.fcc\custom_cabundle.pem"
set "CURL_CA_BUNDLE=%USERPROFILE%\.fcc\custom_cabundle.pem"
set "NODE_EXTRA_CA_CERTS=%USERPROFILE%\.fcc\custom_cabundle.pem"
set "PYTHONPATH=%USERPROFILE%\.fcc\python_patch"

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
py -3.11 app.py
