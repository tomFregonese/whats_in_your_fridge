@echo off
cd /d %~dp0

if not exist .env (
    copy .env.example .env >nul
)

docker compose up -d --build

echo.
echo What's in your fridge? is starting up.
echo Open http://127.0.0.1:8080 (or the APP_PORT set in .env) once the containers report healthy.
