"""Client for the local `nlp` service (see `nlp/main.py`) — a small
FastAPI wrapper around a grammar-constrained local chat model, running as
its own Docker Compose service, reachable only from `api` over the
internal Docker network (same "no `ports:`" convention as this service
itself — see `docker-compose.yml`).

Kept separate from `agent/client.py` on purpose: that module talks to
OpenRouter specifically (auth token, `:free` catalog, the whole
`OpenRouterError` hierarchy); this one talks to a local, unauthenticated,
always-free service. Same shape as `stt_client.py` for the same reason.

Two capabilities, same service: `structure()` (dictation transcript ->
structured ingredient/quantity rows) and `find_duplicates()` (fridge-
stock names that look like the same real ingredient — see
`agent/duplicate_check.py`, the only caller of the latter).
"""

import httpx

from app.config import settings
from app.services.exceptions import NlpUnavailableError

_REQUEST_TIMEOUT_SECONDS = 60.0  # a cold model load on first use can take a few seconds


def structure(*, transcript: str) -> dict[str, object]:
    try:
        response = httpx.post(
            f"{settings.nlp_url}/structure",
            json={"transcript": transcript},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise NlpUnavailableError(
            "Could not reach the local structuring service — check that the `nlp` "
            "container is running."
        ) from exc

    return dict(response.json())


def find_duplicates(*, ingredient_names: list[str]) -> dict[str, object]:
    try:
        response = httpx.post(
            f"{settings.nlp_url}/find-duplicates",
            json={"ingredient_names": ingredient_names},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise NlpUnavailableError(
            "Could not reach the local structuring service — check that the `nlp` "
            "container is running."
        ) from exc

    return dict(response.json())
