import json
from unittest.mock import MagicMock, patch

import pytest
from openai.types.chat import ChatCompletionMessageFunctionToolCall, ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_function_tool_call import Function

from app.agent import loop
from app.services.exceptions import AgentResponseInvalidError

VALID_PLATS_ARGS = json.dumps(
    {
        "plats": [
            {
                "nom": "Carrot soup",
                "description": "Simple soup",
                "portions": 4,
                "ingredients": [{"nom": "carrot", "quantite": "3"}],
                "etapes": ["Boil.", "Blend."],
            }
        ],
        "notes_generales": None,
    }
)

VALID_PRECISION_ARGS = json.dumps({"question": "How many people?", "options": ["2", "4"]})


def _tool_call(call_id: str, name: str, arguments: str) -> ChatCompletionMessageFunctionToolCall:
    # A real instance rather than a mock: loop.py narrows on
    # `isinstance(call, ChatCompletionMessageFunctionToolCall)`, which a
    # bare MagicMock (even with `spec=`) doesn't reliably satisfy for a
    # pydantic model's declared fields.
    return ChatCompletionMessageFunctionToolCall(
        id=call_id, type="function", function=Function(name=name, arguments=arguments)
    )


def _message(
    *,
    tool_calls: list[ChatCompletionMessageFunctionToolCall] | None = None,
    content: str | None = None,
) -> MagicMock:
    message = MagicMock()
    message.tool_calls = tool_calls
    message.content = content
    return message


def _messages() -> list[ChatCompletionMessageParam]:
    return [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]


def test_loop_returns_plats_proposed_on_valid_tool_call() -> None:
    message = _message(tool_calls=[_tool_call("call_1", "proposer_plats", VALID_PLATS_ARGS)])
    with patch("app.agent.loop.client.complete_with_tools", return_value=message) as mock_complete:
        result = loop.run(token="tok", model="m", messages=_messages())

    assert isinstance(result, loop.PlatsProposed)
    assert result.args.plats[0].nom == "Carrot soup"
    mock_complete.assert_called_once()


def test_loop_returns_clarification_needed_on_valid_tool_call() -> None:
    message = _message(
        tool_calls=[_tool_call("call_1", "demander_precision", VALID_PRECISION_ARGS)]
    )
    with patch("app.agent.loop.client.complete_with_tools", return_value=message):
        result = loop.run(token="tok", model="m", messages=_messages())

    assert isinstance(result, loop.ClarificationNeeded)
    assert result.question == "How many people?"
    assert result.options == ["2", "4"]
    # The persisted conversation must end with the assistant's tool call,
    # ready for `pending_tool_call_id` / `respond()` to resume from.
    last = result.messages[-1]
    assert last["role"] == "assistant"
    assert last["tool_calls"][0]["id"] == "call_1"  # type: ignore[index]


def test_loop_retries_on_invalid_json_then_succeeds() -> None:
    bad = _message(tool_calls=[_tool_call("call_1", "proposer_plats", "{not valid json")])
    good = _message(tool_calls=[_tool_call("call_2", "proposer_plats", VALID_PLATS_ARGS)])
    with patch(
        "app.agent.loop.client.complete_with_tools", side_effect=[bad, good]
    ) as mock_complete:
        result = loop.run(token="tok", model="m", messages=_messages())

    assert isinstance(result, loop.PlatsProposed)
    assert mock_complete.call_count == 2


def test_loop_retries_when_no_tool_call_then_succeeds() -> None:
    plain_text = _message(tool_calls=None, content="Sure, here are some ideas...")
    good = _message(tool_calls=[_tool_call("call_1", "proposer_plats", VALID_PLATS_ARGS)])
    with patch(
        "app.agent.loop.client.complete_with_tools", side_effect=[plain_text, good]
    ) as mock_complete:
        result = loop.run(token="tok", model="m", messages=_messages())

    assert isinstance(result, loop.PlatsProposed)
    assert mock_complete.call_count == 2


def test_loop_raises_after_exhausting_retries() -> None:
    bad = _message(tool_calls=[_tool_call("call_1", "proposer_plats", "{not valid json")])
    with (
        patch("app.agent.loop.client.complete_with_tools", return_value=bad) as mock_complete,
        pytest.raises(AgentResponseInvalidError),
    ):
        loop.run(token="tok", model="m", messages=_messages())

    assert mock_complete.call_count == loop.MAX_ATTEMPTS


def test_loop_treats_unknown_tool_as_retryable() -> None:
    unknown = _message(tool_calls=[_tool_call("call_1", "mystery_tool", "{}")])
    good = _message(tool_calls=[_tool_call("call_2", "proposer_plats", VALID_PLATS_ARGS)])
    with patch("app.agent.loop.client.complete_with_tools", side_effect=[unknown, good]):
        result = loop.run(token="tok", model="m", messages=_messages())

    assert isinstance(result, loop.PlatsProposed)


def test_pending_tool_call_id_extracts_from_last_message() -> None:
    messages: list[ChatCompletionMessageParam] = [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "call_42", "type": "function", "function": {"name": "x", "arguments": "{}"}}
            ],
        },
    ]

    assert loop.pending_tool_call_id(messages) == "call_42"


def test_pending_tool_call_id_raises_without_pending_call() -> None:
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": "hi"}]

    with pytest.raises(AgentResponseInvalidError):
        loop.pending_tool_call_id(messages)


def test_serialize_deserialize_round_trips() -> None:
    messages = _messages()

    restored = loop.deserialize_messages(loop.serialize_messages(messages))

    assert restored == messages
