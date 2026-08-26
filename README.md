# What's in your fridge?

Self-hosted AI app that suggests batch-cooking meals for the week based on what's in your fridge,
remembers past suggestions to keep things varied, and collects feedback after each meal
(liked/disliked, why).

100% local: no network exposure, no running cost for the household (OpenRouter `:free` models).

## Running the app

Requirement: [Docker Desktop](https://www.docker.com/products/docker-desktop/).

- **Mac/Linux**: double-click `start.sh` (or `./start.sh` in a terminal)
- **Windows**: double-click `start.bat`

Then open http://127.0.0.1:8080 in a browser. On first launch, the UI walks you through setup
(app password, OpenRouter token, model choice, allergies, portions) — nothing to edit by hand.

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

## Project status

Work in progress — see the V1 plan for the full architecture and build milestones.
