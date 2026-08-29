"""Client for the local `nlp` service (see `nlp/main.py`) — a small
FastAPI wrapper around a grammar-constrained local chat model, running as
its own Docker Compose service, reachable only from `api` over the
internal Docker network (same "no `ports:`" convention as this service
itself — see `docker-compose.yml`).

Kept separate from `agent/client.py` on purpose: that module talks to
OpenRouter specifically (auth token, `:free` catalog, the whole
`OpenRouterError` hierarchy); this one talks to a local, unauthenticated,
always-free service that only ever does one thing — structure a dictated
transcript into ingredient/quantity rows. Same shape as `stt_client.py`
for the same reason.
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
