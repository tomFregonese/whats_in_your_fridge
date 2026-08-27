"""Minimal OpenRouter chat-completions client.

Wraps the OpenAI SDK pointed at OpenRouter's endpoint (they're API
compatible). Turns SDK failures into this app's own typed exceptions, so
callers never need to know about the `openai` package.

The token and model are passed in by the caller (sourced from
`security.service.SecurityService.get_token()` and
`settings.openrouter_model_id` respectively) — this module stays stateless
and has no knowledge of the vault, the DB, or FastAPI's DI.
"""

from collections.abc import Callable, Iterable

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
    ChatCompletionToolMessageParam,
)
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall

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

# Minimum request for connection testing — cheap/fast models handle this.
_MINIMAL_MESSAGES: list[ChatCompletionMessageParam] = [
    {"role": "user", "content": "ok"},
    {"role": "assistant", "content": "ok"},
]
_MINIMAL_TOOLS: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "done",
            "description": "Signal that the test is complete.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }
]


def complete(
    *,
    token: str,
    model: str,
    messages: Iterable[ChatCompletionMessageParam],
) -> str:
    """Sends one chat-completion request (no tools) and returns the
    assistant's text. Used for simple, non-agentic calls — the tool-calling
    loop uses `complete_with_tools` instead.
    """
    message = _request(token=token, model=model, messages=messages, tools=None)
    if not message.content:
        raise OpenRouterEmptyResponseError("OpenRouter returned an empty message.")
    return message.content


def complete_with_tools(
    *,
    token: str,
    model: str,
    messages: Iterable[ChatCompletionMessageParam],
    tools: Iterable[ChatCompletionToolParam],
) -> ChatCompletionMessage:
    """Sends one chat-completion request with tools available and returns
    the raw assistant message — the caller (`agent/loop.py`) inspects
    `.tool_calls`, since interpreting them is the loop's job, not this
    module's.
    """
    return _request(token=token, model=model, messages=messages, tools=tools)


def _request(
    *,
    token: str,
    model: str,
    messages: Iterable[ChatCompletionMessageParam],
    tools: Iterable[ChatCompletionToolParam] | None,
) -> ChatCompletionMessage:
    """Raises an `OpenRouterError` subclass on any failure — the raw
    `openai` SDK exceptions never escape this module.
    """
    client = OpenAI(api_key=token, base_url=OPENROUTER_BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS)

    try:
        if tools is None:
            response = client.chat.completions.create(model=model, messages=messages)
        else:
            response = client.chat.completions.create(model=model, messages=messages, tools=tools)
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

    return response.choices[0].message


def stream_complete_with_tools(
    *,
    token: str,
    model: str,
    messages: Iterable[ChatCompletionMessageParam],
    tools: Iterable[ChatCompletionToolParam],
    reasoning_callback: Callable[[str], None],
) -> ChatCompletionMessage:
    """Calls the model with streaming enabled, forwarding any reasoning
    tokens to `reasoning_callback` as they arrive (for models that expose
    them in the stream, e.g. DeepSeek R1 via OpenRouter).

    Reconstructs the full `ChatCompletionMessage` from streaming chunks
    so the caller can inspect `.tool_calls` the same way as non-streaming.

    Raises the same `OpenRouterError` subclasses on failure.
    """
    client = OpenAI(api_key=token, base_url=OPENROUTER_BASE_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    messages_list: list[ChatCompletionMessageParam] = list(messages)
    tools_list: list[ChatCompletionToolParam] = list(tools)

    try:
        stream = client.chat.completions.create(
            model=model, messages=messages_list, tools=tools_list, stream=True
        )
    except AuthenticationError as exc:
        raise OpenRouterAuthError("OpenRouter rejected the configured API token.") from exc
    except RateLimitError as exc:
        raise OpenRouterRateLimitError(
            "OpenRouter's rate limit was exceeded — try again shortly."
        ) from exc
    except APITimeoutError as exc:
        raise OpenRouterTimeoutError(
            f"OpenRouter did not respond within {REQUEST_TIMEOUT_SECONDS:.0f}s."
        ) from exc
    except APIConnectionError as exc:
        raise OpenRouterConnectionError("Could not reach OpenRouter.") from exc

    collected_content: list[str] = []
    tool_calls: dict[int, dict] = {}
    finish_reason: str | None = None

    for chunk in stream:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        finish_reason = chunk.choices[0].finish_reason

        # Reasoning tokens (OpenRouter / DeepSeek etc. via delta.reasoning)
        reasoning = getattr(delta, "reasoning", None)
        if reasoning:
            reasoning_callback(reasoning)

        # Regular content
        if delta.content:
            collected_content.append(delta.content)

        # Tool calls (streamed incrementally — merge by index)
        if delta.tool_calls:
            for tc in delta.tool_calls:
                if not isinstance(tc, ChoiceDeltaToolCall):
                    continue
                idx = tc.index
                if idx not in tool_calls:
                    tool_calls[idx] = {
                        "id": tc.id or "",
                        "function": {"name": "", "arguments": ""},
                    }
                if tc.id:
                    tool_calls[idx]["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        tool_calls[idx]["function"]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls[idx]["function"]["arguments"] += tc.function.arguments

    content = "".join(collected_content) or None

    # Rebuild tool calls into the SDK's expected param format
    rebuilt_tool_calls: list[ChatCompletionToolMessageParam] | None = None
    if tool_calls:
        rebuilt_tool_calls = []
        for idx in sorted(tool_calls):
            tc = tool_calls[idx]
            rebuilt_tool_calls.append({
                "id": tc["id"],
                "type": "function",
                "function": tc["function"],
            })

    return ChatCompletionMessage(
        role="assistant",
        content=content,
        tool_calls=rebuilt_tool_calls,  # type: ignore[arg-type]
    )


def test_connection(*, token: str, model: str) -> bool:
    """Sends a minimal request to verify the token and model work together.
    Returns ``True`` on success, ``False`` on any auth/model error.
    """
    try:
        stream_complete_with_tools(
            token=token,
            model=model,
            messages=_MINIMAL_MESSAGES,
            tools=_MINIMAL_TOOLS,
            reasoning_callback=lambda _: None,
        )
        return True
    except (OpenRouterAuthError, OpenRouterConnectionError, OpenRouterEmptyResponseError):
        return False
