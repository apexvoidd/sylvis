@echo off
title Free Claude Code Launcher (NVIDIA NIM Proxy)
color 0A
echo ===================================================
echo        STARTING FREE CLAUDE CODE SERVICE
echo ===================================================
echo.
echo [System Check] Checking for fcc-server...
where fcc-server >nul 2>nul
if %errorlevel% neq 0 (
    echo [System Check] fcc-server not in default PATH. Checking user local bin...
    if exist "%USERPROFILE%\.local\bin\fcc-server.exe" (
        set "PATH=%PATH%;%USERPROFILE%\.local\bin"
        echo [System Check] Added fcc-server to temporary session PATH.
    ) else (
        echo [ERROR] fcc-server could not be found.
        echo Please install it or make sure it is in your PATH.
        pause
        exit /b 1
    )
)

echo [System Check] Starting fcc-server proxy on port 8082...

if exist "%USERPROFILE%\.fcc\custom_cabundle.pem" (
    echo [System Check] Custom SSL certificate bundle detected. Applying environment configurations...
    set "SSL_CERT_FILE=%USERPROFILE%\.fcc\custom_cabundle.pem"
    set "REQUESTS_CA_BUNDLE=%USERPROFILE%\.fcc\custom_cabundle.pem"
    set "CURL_CA_BUNDLE=%USERPROFILE%\.fcc\custom_cabundle.pem"
    set "NODE_EXTRA_CA_CERTS=%USERPROFILE%\.fcc\custom_cabundle.pem"
    set "PYTHONPATH=%USERPROFILE%\.fcc\python_patch"
)

start "fcc-server-proxy" fcc-server

echo.
echo ===================================================
echo [System Check] Setting up terminal environment...
echo [System Check] Setting CLAUDE_BASE_URL to http://localhost:8082
echo ===================================================
echo.
echo Running Claude Code in free proxy mode...
set CLAUDE_BASE_URL=http://localhost:8082
call claude
pause
