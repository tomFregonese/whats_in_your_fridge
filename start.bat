@echo off
cd /d %~dp0

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker was not found on this machine.
    echo Install Docker Desktop first: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo Docker is installed but doesn't seem to be running.
    echo Start Docker Desktop, then run this script again.
    pause
    exit /b 1
)

rem Prefer the modern "docker compose" plugin; fall back to the standalone
rem docker-compose.exe otherwise.
set COMPOSE=docker compose
docker compose version >nul 2>nul
if errorlevel 1 (
    where docker-compose >nul 2>nul
    if errorlevel 1 (
        echo Docker Compose was not found ^(neither "docker compose" nor "docker-compose"^).
        echo Install it: https://docs.docker.com/compose/install/
        pause
        exit /b 1
    )
    set COMPOSE=docker-compose
)

if not exist .env (
    copy .env.example .env >nul
)

rem This script only ever *launches* the images already built by
rem update.bat — it never builds. Fails clearly instead of silently
rem building, so what's actually running is never a surprise.
for /f "delims=" %%I in ('%COMPOSE% config --images') do (
    docker image inspect %%I >nul 2>nul
    if errorlevel 1 (
        echo No built image found for: %%I
        echo Run update.bat first to build it, then run this script again.
        pause
        exit /b 1
    )
)

echo Starting What's in your fridge?...

rem --wait blocks until both containers report healthy (see each
rem Dockerfile's HEALTHCHECK) instead of just "started", so the URL below
rem is only printed once the app is actually ready to open.
%COMPOSE% up -d --wait --wait-timeout 120
if errorlevel 1 (
    echo.
    echo Something went wrong starting the app - see the errors above, or run
    echo "%COMPOSE% logs" for more detail.
    pause
    exit /b 1
)

echo.
echo Ready! Open http://127.0.0.1:8080 (or the APP_PORT set in .env) in your browser.
pause
