# What's in your fridge?

Self-hosted AI app that suggests batch-cooking meals for the week based on what's in your fridge,
remembers past suggestions to keep things varied, and collects feedback after each meal
(liked/disliked, why).

100% local: no network exposure, no running cost for the household (OpenRouter `:free` models).

## Running the app

Requirement: [Docker Desktop](https://www.docker.com/products/docker-desktop/), running.

- **Mac/Linux**: double-click `start.sh` (or `./start.sh` in a terminal)
- **Windows**: double-click `start.bat`

The script builds the images, starts both containers, and waits until they report healthy before
printing the URL to open — usually a few seconds, longer the very first time while images build.

On first launch, the UI walks you through setup (app password, OpenRouter token, model choice,
allergies, portions) — nothing to edit by hand.

### Changing the port

The app listens on `127.0.0.1:8080` by default. If that port is already taken, edit `APP_PORT` in
`.env` (created from `.env.example` on first run) and restart with the same script.

### Stopping / restarting

```
docker compose down     # stop
docker compose up -d    # restart (no rebuild)
```

Your data isn't affected either way — it lives outside the containers (see below).

### Updating

Pull the latest code, then run `start.sh` / `start.bat` again — it rebuilds the images and applies
any database schema changes automatically before starting. Your `data/fridge.db` is untouched.

### Troubleshooting

`docker compose ps` shows both containers' health status. If one is stuck `unhealthy` or keeps
restarting, `docker compose logs api` or `docker compose logs frontend` has the detail.

## Data and backups

All data (preferences, history, encrypted OpenRouter token) lives in a single SQLite file:
`data/fridge.db`, next to this README.

There is **no automatic backup** in V1. To back up your data, copy that file yourself while the
app is stopped (`docker compose down`).

⚠️ The OpenRouter token is encrypted with a key derived from your app password, which is never
stored on disk. A copy of `fridge.db` alone therefore stays readable for the rest of your data,
but the OpenRouter token can only be decrypted by re-entering that same password in the app. If
the password is lost, there is no recovery path in V1 — the only option is to clear the stored
token and re-enter it.
