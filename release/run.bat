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
    echo Start Docker Desktop, then run this again.
    pause
    exit /b 1
)

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

echo Downloading What's in your fridge? - this can take a few minutes the first time.
%COMPOSE% pull
if errorlevel 1 (
    echo.
    echo Something went wrong downloading the app - see the errors above.
    pause
    exit /b 1
)

echo Starting...
%COMPOSE% up -d --wait --wait-timeout 120
if errorlevel 1 (
    echo.
    echo Something went wrong starting the app - see the errors above, or run
    echo "%COMPOSE% logs" for more detail.
    pause
    exit /b 1
)

set APP_PORT=8080
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="APP_PORT" set APP_PORT=%%b
)

echo.
echo Ready! Opening http://127.0.0.1:%APP_PORT% in your browser...
start "" "http://127.0.0.1:%APP_PORT%"
pause
