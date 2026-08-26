from unittest.mock import MagicMock, patch

import httpx2
import openai
import pytest

from app.agent import client
from app.services.exceptions import (
    OpenRouterAuthError,
    OpenRouterConnectionError,
    OpenRouterEmptyResponseError,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
)

_REQUEST = httpx2.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
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
    response = httpx2.Response(401, request=_REQUEST, json={"error": "bad token"})
    sdk_error = openai.AuthenticationError("bad token", response=response, body=None)
    mock_openai = _mock_client(side_effect=sdk_error)
    with patch("app.agent.client.OpenAI", mock_openai), pytest.raises(OpenRouterAuthError):
        client.complete(token="tok", model="m", messages=_MESSAGES)


def test_complete_wraps_rate_limit_error() -> None:
    response = httpx2.Response(429, request=_REQUEST, json={"error": "slow down"})
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
