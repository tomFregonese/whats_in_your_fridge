"""Client for the local `stt` service (see `stt/main.py`) — a small
FastAPI wrapper around `faster-whisper`, running as its own Docker Compose
service, reachable only from `api` over the internal Docker network (same
"no `ports:`" convention as this service itself — see `docker-compose.yml`).

Kept separate from `agent/client.py` on purpose: that module talks to
OpenRouter specifically (auth token, `:free` catalog, the whole
`OpenRouterError` hierarchy); this one talks to a local, unauthenticated,
always-free service that only ever does one thing — turn audio into text,
using the one Whisper size the `stt` service bakes in (`"base"` — the best
speed/accuracy tradeoff of the three sizes tried; see the project plan).
"""

import httpx

from app.config import settings
from app.services.exceptions import SttUnavailableError

_REQUEST_TIMEOUT_SECONDS = 120.0  # a cold model load on first use can be slow


def transcribe(*, audio_base64: str, audio_format: str) -> str:
    try:
        response = httpx.post(
            f"{settings.stt_url}/transcribe",
            json={"audio_base64": audio_base64, "audio_format": audio_format},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SttUnavailableError(
            "Could not reach the local speech-to-text service — check that the `stt` "
            "container is running."
        ) from exc

    return str(response.json()["text"])
