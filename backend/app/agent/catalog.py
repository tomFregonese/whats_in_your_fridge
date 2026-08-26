"""Fetches and caches OpenRouter's `:free` model catalog.

Used by the model picker (Onboarding/Settings) today. A later milestone
adds an availability check that reuses this same cache to warn the user if
their chosen model disappears from the catalog.
"""

import time
from dataclasses import dataclass

import httpx

from app.services.exceptions import CatalogUnavailableError

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
CACHE_TTL_SECONDS = 300  # avoids re-fetching on every screen load


@dataclass
class FreeModel:
    id: str
    name: str
    context_length: int | None
    description: str | None


_cache: list[FreeModel] | None = None
_cache_expires_at: float = 0.0


def list_free_models(*, force_refresh: bool = False) -> list[FreeModel]:
    """Returns every catalog entry whose id ends with `:free`, cached in
    memory for `CACHE_TTL_SECONDS`.
    """
    global _cache, _cache_expires_at
    now = time.monotonic()
    if not force_refresh and _cache is not None and now < _cache_expires_at:
        return _cache

    try:
        response = httpx.get(OPENROUTER_MODELS_URL, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise CatalogUnavailableError("Could not reach OpenRouter's model catalog.") from exc

    models = [
        FreeModel(
            id=entry["id"],
            name=entry.get("name") or entry["id"],
            context_length=entry.get("context_length"),
            description=entry.get("description"),
        )
        for entry in payload.get("data", [])
        if entry.get("id", "").endswith(":free")
    ]

    _cache = models
    _cache_expires_at = now + CACHE_TTL_SECONDS
    return models


def clear_cache() -> None:
    """Testing convenience — production code relies on the TTL instead."""
    global _cache, _cache_expires_at
    _cache = None
    _cache_expires_at = 0.0
