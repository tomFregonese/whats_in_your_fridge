@echo off
cd /d %~dp0

rem Rebuilds the app's images from the current source — this is the only
rem script that ever builds (see start.bat, which only launches whatever
rem was last built here). Doesn't touch anything in .\data: images are
rem separate from your data volume, so your fridge.db is never at risk.
rem
rem Safe to run while the app is up: the running containers keep using
rem the old image until you run start.bat again, which picks up the new one.

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

echo Rebuilding What's in your fridge? images - this can take a minute.

%COMPOSE% build
if errorlevel 1 (
    echo.
    echo Something went wrong rebuilding the images - see the errors above.
    pause
    exit /b 1
)

echo.
echo Images rebuilt. Run start.bat to launch the new version.
pause
