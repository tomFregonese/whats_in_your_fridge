# What's in your fridge?

Self-hosted AI app that suggests batch-cooking meals for the week based on what's in your fridge,
remembers past suggestions to keep things varied, and collects feedback after each meal
(liked/disliked, why).

100% local: no network exposure, no running cost for the household (OpenRouter `:free` models).

## Running the app

Requirement: Docker + Docker Compose, running — [Docker Desktop](https://www.docker.com/products/docker-desktop/)
is the easiest way to get both (Mac/Windows/Linux); [Colima](https://github.com/abiosoft/colima) +
Homebrew's `docker-compose` also works on Mac/Linux.

- **First launch**: run `update.sh` (`update.bat` on Windows) once to build the images, then
  `start.sh` (`start.bat`) to launch.
- **Every launch after that**: just `start.sh` / `start.bat`.

Both work with either the modern `docker compose` plugin or the standalone `docker-compose`
binary, whichever they find — the commands below use `docker compose`, swap in `docker-compose`
if that's what's on your machine.

`start.sh`/`start.bat` only ever *launch* the images already built by `update.sh`/`update.bat` —
they never build, and fail with a clear message if no image has been built yet, rather than
silently building one. This keeps what's actually running predictable: it only ever changes when
you explicitly ask it to, via `update.sh`. Waits until all containers report healthy before
printing the URL to open.

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

Pull the latest code, then:

```
./update.sh   # rebuilds the images from the new source — safe to run while the app is up,
              # the running containers keep using the old image until the next step
./start.sh    # picks up the newly built image and restarts; DB schema changes apply automatically
```

Or `./redeploy.sh` (`redeploy.bat`) to run both in one go.

Your `data/fridge.db` is untouched by either step.

### Troubleshooting

`docker compose ps` shows every container's health status (`frontend`, `api`, and two internal-only
helper services: `stt` for local speech-to-text and `nlp` for local dictation structuring — see
"Voice dictation" below). If one is stuck `unhealthy` or keeps restarting, `docker compose logs
<service>` has the detail.

## Voice dictation

Dictating fridge items (the mic button on the Fridge page) is fully local and needs no OpenRouter
token: audio is transcribed by a small self-hosted Whisper model (`stt` service), then structured
into ingredient/quantity rows by a small self-hosted chat model (`nlp` service, Qwen2.5-1.5B) —
neither step reaches the internet. Both models are baked into their images at `update.sh` time, so
the first dictation after `start.sh` works immediately, no download.

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
