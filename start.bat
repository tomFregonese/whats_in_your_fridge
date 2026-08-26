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

if not exist .env (
    copy .env.example .env >nul
)

echo Starting What's in your fridge? - this can take a minute on first launch.

rem --wait blocks until both containers report healthy (see each
rem Dockerfile's HEALTHCHECK) instead of just "started", so the URL below
rem is only printed once the app is actually ready to open.
docker compose up -d --build --wait --wait-timeout 120
if errorlevel 1 (
    echo.
    echo Something went wrong starting the app - see the errors above, or run
    echo "docker compose logs" for more detail.
    pause
    exit /b 1
)

echo.
echo Ready! Open http://127.0.0.1:8080 (or the APP_PORT set in .env) in your browser.
pause
