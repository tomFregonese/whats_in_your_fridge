@echo off
cd /d %~dp0

set COMPOSE=docker compose
docker compose version >nul 2>nul
if errorlevel 1 (
    where docker-compose >nul 2>nul
    if errorlevel 1 (
        echo Docker Compose was not found ^(neither "docker compose" nor "docker-compose"^).
        pause
        exit /b 1
    )
    set COMPOSE=docker-compose
)

echo Stopping What's in your fridge?...
%COMPOSE% down
echo Stopped. Your data (data\fridge.db) is untouched - run.bat starts it again anytime.
pause
