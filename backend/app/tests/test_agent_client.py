from collections.abc import Iterator
from unittest.mock import MagicMock, patch

# The installed `openai` SDK's exceptions (`AuthenticationError`, etc.) now
# type their `request`/`response` args as `httpx2`, its own successor to
# `httpx`, so that's what these fixtures need to build.
import httpx2 as httpx
import openai
import pytest

from app.agent import client
from app.services.exceptions import (
    OpenRouterAuthError,
    OpenRouterConnectionError,
    OpenRouterEmptyResponseError,
    OpenRouterRateLimitError,
    OpenRouterRequestError,
    OpenRouterTimeoutError,
)

_REQUEST = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
_MESSAGES: list[openai.types.chat.ChatCompletionMessageParam] = [
    {"role": "user", "content": "hello"}
]


def _mock_client(side_effect: object = None, return_value: object = None) -> MagicMock:
    mock_openai = MagicMock()
    if side_effect is not None:
        mock_openai.return_value.chat.completions.create.side_effect = side_effect
    else:
        mock_openai.return_value.chat.completions.create.return_value = return_value
    return mock_openai


def _completion_with_content(content: str | None) -> MagicMock:
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content=content))]
    return completion


def test_complete_returns_message_content() -> None:
    mock_openai = _mock_client(return_value=_completion_with_content("Try a stir-fry."))
    with patch("app.agent.client.OpenAI", mock_openai):
        result = client.complete(token="tok", model="some/model:free", messages=_MESSAGES)

    assert result == "Try a stir-fry."


def test_complete_passes_token_model_and_base_url() -> None:
    mock_openai = _mock_client(return_value=_completion_with_content("ok"))
    with patch("app.agent.client.OpenAI", mock_openai):
        client.complete(token="secret-token", model="some/model:free", messages=_MESSAGES)

    mock_openai.assert_called_once_with(
        api_key="secret-token",
        base_url=client.OPENROUTER_BASE_URL,
        timeout=client.REQUEST_TIMEOUT_SECONDS,
    )
    mock_openai.return_value.chat.completions.create.assert_called_once_with(
        model="some/model:free", messages=_MESSAGES
    )


def test_complete_raises_on_empty_choices() -> None:
    completion = MagicMock(choices=[])
    mock_openai = _mock_client(return_value=completion)
    with patch("app.agent.client.OpenAI", mock_openai), pytest.raises(OpenRouterEmptyResponseError):
        client.complete(token="tok", model="m", messages=_MESSAGES)


def test_complete_raises_on_blank_content() -> None:
    mock_openai = _mock_client(return_value=_completion_with_content(None))
    with patch("app.agent.client.OpenAI", mock_openai), pytest.raises(OpenRouterEmptyResponseError):
        client.complete(token="tok", model="m", messages=_MESSAGES)


def test_complete_wraps_authentication_error() -> None:
    response = httpx.Response(401, request=_REQUEST, json={"error": "bad token"})
    sdk_error = openai.AuthenticationError("bad token", response=response, body=None)
    mock_openai = _mock_client(side_effect=sdk_error)
    with patch("app.agent.client.OpenAI", mock_openai), pytest.raises(OpenRouterAuthError):
        client.complete(token="tok", model="m", messages=_MESSAGES)


def test_complete_wraps_rate_limit_error() -> None:
    response = httpx.Response(429, request=_REQUEST, json={"error": "slow down"})
    sdk_error = openai.RateLimitError("slow down", response=response, body=None)
    mock_openai = _mock_client(side_effect=sdk_error)
    with patch("app.agent.client.OpenAI", mock_openai), pytest.raises(OpenRouterRateLimitError):
        client.complete(token="tok", model="m", messages=_MESSAGES)


def test_complete_wraps_timeout_error() -> None:
    sdk_error = openai.APITimeoutError(request=_REQUEST)
    mock_openai = _mock_client(side_effect=sdk_error)
    with patch("app.agent.client.OpenAI", mock_openai), pytest.raises(OpenRouterTimeoutError):
        client.complete(token="tok", model="m", messages=_MESSAGES)


def test_complete_wraps_connection_error() -> None:
    sdk_error = openai.APIConnectionError(request=_REQUEST)
    mock_openai = _mock_client(side_effect=sdk_error)
    with patch("app.agent.client.OpenAI", mock_openai), pytest.raises(OpenRouterConnectionError):
        client.complete(token="tok", model="m", messages=_MESSAGES)


def test_complete_wraps_bad_request_error_with_openrouter_detail() -> None:
    # Regression test: `BadRequestError` (and every other `APIStatusError`
    # subtype not individually caught — NotFoundError, ConflictError,
    # UnprocessableEntityError, InternalServerError...) used to escape this
    # module as a raw `openai` exception, surfacing as an opaque 500
    # instead of the `OpenRouterError` this module promises to always
    # raise. This is exactly what a model rejecting unsupported input
    # (e.g. audio — see `agent/dictation.py`) looks like.
    response = httpx.Response(400, request=_REQUEST, json={"error": {"message": "bad input"}})
    sdk_error = openai.BadRequestError(
        "bad request", response=response, body={"error": {"message": "bad input"}}
    )
    mock_openai = _mock_client(side_effect=sdk_error)
    with (
        patch("app.agent.client.OpenAI", mock_openai),
        pytest.raises(OpenRouterRequestError) as exc_info,
    ):
        client.complete(token="tok", model="m", messages=_MESSAGES)

    assert "bad input" in str(exc_info.value)
    assert "400" in str(exc_info.value)


def test_complete_wraps_bad_request_error_without_structured_body() -> None:
    response = httpx.Response(400, request=_REQUEST)
    sdk_error = openai.BadRequestError("bad request", response=response, body=None)
    mock_openai = _mock_client(side_effect=sdk_error)
    with (
        patch("app.agent.client.OpenAI", mock_openai),
        pytest.raises(OpenRouterRequestError) as exc_info,
    ):
        client.complete(token="tok", model="m", messages=_MESSAGES)

    assert "bad request" in str(exc_info.value)


def _stream_that_raises(exc: Exception) -> object:
    """A fake streaming response whose iteration fails partway through —
    `chat.completions.create(..., stream=True)` itself never raises (it
    returns an iterator without making the request), so this is the only
    way to exercise the failure path a stalled/dropped stream takes."""

    def _gen() -> Iterator[object]:
        raise exc
        yield  # pragma: no cover - unreachable; makes this a generator

    return _gen()


def test_stream_complete_with_tools_wraps_mid_stream_timeout() -> None:
    # Regression test: a stall *while iterating* the stream (the model
    # taking too long to send its next chunk) used to escape this module as
    # a raw `openai`/`httpx` exception instead of the `OpenRouterTimeoutError`
    # this module promises elsewhere — see
    # `agent/client.py::stream_complete_with_tools`. Callers' generic
    # `except Exception` then reported it with an unhelpful message instead
    # of a clear, actionable one.
    sdk_error = openai.APITimeoutError(request=_REQUEST)
    mock_openai = _mock_client(return_value=_stream_that_raises(sdk_error))
    with patch("app.agent.client.OpenAI", mock_openai), pytest.raises(OpenRouterTimeoutError):
        client.stream_complete_with_tools(
            token="tok",
            model="m",
            messages=_MESSAGES,
            tools=[],
            reasoning_callback=lambda _: None,
        )


def test_stream_complete_with_tools_wraps_mid_stream_connection_error() -> None:
    sdk_error = openai.APIConnectionError(request=_REQUEST)
    mock_openai = _mock_client(return_value=_stream_that_raises(sdk_error))
    with patch("app.agent.client.OpenAI", mock_openai), pytest.raises(OpenRouterConnectionError):
        client.stream_complete_with_tools(
            token="tok",
            model="m",
            messages=_MESSAGES,
            tools=[],
            reasoning_callback=lambda _: None,
        )


def test_stream_complete_with_tools_wraps_provider_error_event() -> None:
    # Regression test for the real-world failure this was added for: when
    # the model *provider* behind a `:free` model fails mid-generation,
    # OpenRouter sends an in-stream `{"error": {...}}` SSE event rather
    # than a bad HTTP status, which the `openai` SDK surfaces as a bare
    # `APIError` — not an `APIStatusError`. Before the `except APIError`
    # catch, this escaped as a raw SDK exception whose message ("Provider
    # returned error") then got shown to the user unexplained.
    sdk_error = openai.APIError(
        message="Provider returned error",
        request=_REQUEST,
        body={"message": "Provider returned error"},
    )
    mock_openai = _mock_client(return_value=_stream_that_raises(sdk_error))
    with (
        patch("app.agent.client.OpenAI", mock_openai),
        pytest.raises(OpenRouterRequestError) as exc_info,
    ):
        client.stream_complete_with_tools(
            token="tok",
            model="m",
            messages=_MESSAGES,
            tools=[],
            reasoning_callback=lambda _: None,
        )

    assert "Provider returned error" in str(exc_info.value)
