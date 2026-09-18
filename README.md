# What's in your fridge?

Self-hosted AI app that suggests batch-cooking meals for the week based on what's in your fridge,
remembers past suggestions to keep things varied, and collects feedback after each meal
(liked/disliked, why).

100% local: no network exposure, no running cost for the household (OpenRouter `:free` models).
One exception: the app makes a single outbound, read-only check against GitHub's public release
list to show a "new version available" banner — nothing else ever leaves the machine.

## Just want to try it?

No need to clone this repository or install anything beyond Docker — this only ever runs
prebuilt images pulled from GitHub's container registry (GHCR), never builds anything, and needs
no developer tools.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) if you don't have it
   yet, and make sure it's running.
2. Go to the [Releases page](https://github.com/tomFregonese/whats_in_your_fridge/releases),
   download the latest `whats-in-your-fridge-vX.Y.Z.zip`, and unzip it.
3. Double-click `run.command` (macOS) or `run.bat` (Windows) — or run `run.sh` from a terminal on
   Linux. macOS note: the first double-click will likely be blocked as "from an unidentified
   developer" — right-click the file, choose "Open", confirm once, and it works from then on.
4. Wait — a browser window opens automatically at `http://127.0.0.1:8080` once the app is ready.
5. To close it, double-click `stop.command` / `stop.bat` (or run `stop.sh`). Your data is untouched
   either way.

When the app shows a "new version available" banner, just re-run `run.command`/`run.bat`/`run.sh`
— it pulls the new version and restarts.

## Running from source (development)

Requires cloning this repository — most people should use
[Just want to try it?](#just-want-to-try-it) above instead.

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
