"""Minimal OpenRouter chat-completions client.

Wraps the OpenAI SDK pointed at OpenRouter's endpoint (they're API
compatible). No tool-calling here yet — that's the agent loop, built in a
later milestone (`agent/loop.py`, `agent/tools.py`). This module only
proves the connection works and turns SDK failures into this app's own
typed exceptions, so callers never need to know about the `openai` package.

The token and model are passed in by the caller (sourced from
`security.service.SecurityService.get_token()` and
`settings.openrouter_model_id` respectively) — this module stays stateless
and has no knowledge of the vault, the DB, or FastAPI's DI.
"""

from collections.abc import Iterable

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from openai.types.chat import ChatCompletionMessageParam

from app.services.exceptions import (
    OpenRouterAuthError,
    OpenRouterConnectionError,
    OpenRouterEmptyResponseError,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
)

# Not a secret and not expected to change — a constant, not a setting (see
# the project plan's rationale for what belongs in config vs. code).
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
REQUEST_TIMEOUT_SECONDS = 60.0


def complete(
    *,
    token: str,
    model: str,
    messages: Iterable[ChatCompletionMessageParam],
) -> str:
    """Sends one chat-completion request and returns the assistant's text.

    Raises an `OpenRouterError` subclass on any failure — the raw `openai`
    SDK exceptions never escape this function.
    """
    client = OpenAI(api_key=token, base_url=OPENROUTER_BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS)

    try:
        response = client.chat.completions.create(model=model, messages=messages)
    except AuthenticationError as exc:
        raise OpenRouterAuthError("OpenRouter rejected the configured API token.") from exc
    except RateLimitError as exc:
        raise OpenRouterRateLimitError(
            "OpenRouter's rate limit was exceeded — try again shortly."
        ) from exc
    except APITimeoutError as exc:
        # Must be caught before APIConnectionError: it's a subclass of it.
        raise OpenRouterTimeoutError(
            f"OpenRouter did not respond within {REQUEST_TIMEOUT_SECONDS:.0f}s."
        ) from exc
    except APIConnectionError as exc:
        raise OpenRouterConnectionError("Could not reach OpenRouter.") from exc

    if not response.choices:
        raise OpenRouterEmptyResponseError("OpenRouter returned no choices.")

    content = response.choices[0].message.content
    if not content:
        raise OpenRouterEmptyResponseError("OpenRouter returned an empty message.")

    return content
