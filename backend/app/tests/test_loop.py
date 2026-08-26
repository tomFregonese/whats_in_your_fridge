import json
from unittest.mock import MagicMock, patch

import pytest
from openai.types.chat import ChatCompletionMessageFunctionToolCall, ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_function_tool_call import Function

from app.agent import loop
from app.domain.allergy import Allergy
from app.domain.suggestion import AllergyCheckStatus
from app.services.exceptions import AgentResponseInvalidError

PEANUT_ALLERGY = [Allergy(id=1, ingredient_name="peanut", notes=None)]

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

VIOLATING_PLATS_ARGS = json.dumps(
    {
        "plats": [
            {
                "nom": "Peanut satay",
                "description": "Spicy peanut sauce dish",
                "portions": 4,
                "ingredients": [{"nom": "peanut butter", "quantite": "2 tbsp"}],
                "etapes": ["Mix.", "Serve."],
            }
        ],
        "notes_generales": None,
    }
)

MIXED_PLATS_ARGS = json.dumps(
    {
        "plats": [
            {
                "nom": "Carrot soup",
                "description": "Simple soup",
                "portions": 4,
                "ingredients": [{"nom": "carrot"}],
                "etapes": ["Boil."],
            },
            {
                "nom": "Peanut satay",
                "description": "Spicy peanut sauce dish",
                "portions": 4,
                "ingredients": [{"nom": "peanut butter"}],
                "etapes": ["Mix."],
            },
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


def _run(*, allergies: list[Allergy] | None = None) -> loop.LoopResult:
    return loop.run(
        token="tok", model="m", messages=_messages(), allergies=allergies if allergies else []
    )


def test_loop_returns_plats_proposed_on_valid_tool_call() -> None:
    message = _message(tool_calls=[_tool_call("call_1", "proposer_plats", VALID_PLATS_ARGS)])
    with patch("app.agent.loop.client.complete_with_tools", return_value=message) as mock_complete:
        result = _run()

    assert isinstance(result, loop.PlatsProposed)
    assert result.suggestions[0].dish_name == "Carrot soup"
    assert result.suggestions[0].allergy_check_status == AllergyCheckStatus.OK
    mock_complete.assert_called_once()


def test_loop_returns_clarification_needed_on_valid_tool_call() -> None:
    message = _message(
        tool_calls=[_tool_call("call_1", "demander_precision", VALID_PRECISION_ARGS)]
    )
    with patch("app.agent.loop.client.complete_with_tools", return_value=message):
        result = _run()

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
        result = _run()

    assert isinstance(result, loop.PlatsProposed)
    assert mock_complete.call_count == 2


def test_loop_retries_when_no_tool_call_then_succeeds() -> None:
    plain_text = _message(tool_calls=None, content="Sure, here are some ideas...")
    good = _message(tool_calls=[_tool_call("call_1", "proposer_plats", VALID_PLATS_ARGS)])
    with patch(
        "app.agent.loop.client.complete_with_tools", side_effect=[plain_text, good]
    ) as mock_complete:
        result = _run()

    assert isinstance(result, loop.PlatsProposed)
    assert mock_complete.call_count == 2


def test_loop_raises_after_exhausting_retries() -> None:
    bad = _message(tool_calls=[_tool_call("call_1", "proposer_plats", "{not valid json")])
    with (
        patch("app.agent.loop.client.complete_with_tools", return_value=bad) as mock_complete,
        pytest.raises(AgentResponseInvalidError),
    ):
        _run()

    assert mock_complete.call_count == loop.MAX_ATTEMPTS


def test_loop_treats_unknown_tool_as_retryable() -> None:
    unknown = _message(tool_calls=[_tool_call("call_1", "mystery_tool", "{}")])
    good = _message(tool_calls=[_tool_call("call_2", "proposer_plats", VALID_PLATS_ARGS)])
    with patch("app.agent.loop.client.complete_with_tools", side_effect=[unknown, good]):
        result = _run()

    assert isinstance(result, loop.PlatsProposed)


# --- Allergy check integration (Jalon 8) ---


def test_loop_passes_through_clean_dish_with_no_allergies_configured() -> None:
    message = _message(tool_calls=[_tool_call("call_1", "proposer_plats", VIOLATING_PLATS_ARGS)])
    with patch("app.agent.loop.client.complete_with_tools", return_value=message):
        result = _run(allergies=[])

    assert isinstance(result, loop.PlatsProposed)
    assert result.suggestions[0].dish_name == "Peanut satay"


def test_loop_regenerates_when_dish_violates_allergy() -> None:
    bad = _message(tool_calls=[_tool_call("call_1", "proposer_plats", VIOLATING_PLATS_ARGS)])
    good = _message(tool_calls=[_tool_call("call_2", "proposer_plats", VALID_PLATS_ARGS)])
    with patch(
        "app.agent.loop.client.complete_with_tools", side_effect=[bad, good]
    ) as mock_complete:
        result = _run(allergies=PEANUT_ALLERGY)

    assert isinstance(result, loop.PlatsProposed)
    assert result.suggestions[0].dish_name == "Carrot soup"
    # Regenerated, not a first-try OK — the retry actually happened.
    assert result.suggestions[0].allergy_check_status == AllergyCheckStatus.REGENERATED
    assert mock_complete.call_count == 2

    # The retry request must have explained *why*, so the model had a
    # chance to fix it. `messages` is mutated in place across attempts, so
    # `call_args_list` entries all alias the same final list — search by
    # role/content instead of a fixed index, which the later append (for
    # the successful "good" response) would otherwise shift past.
    final_messages = mock_complete.call_args_list[-1].kwargs["messages"]
    tool_feedback = [m["content"] for m in final_messages if m.get("role") == "tool"]
    assert any(fb and "peanut" in fb and "Peanut satay" in fb for fb in tool_feedback)


def test_loop_drops_dish_that_keeps_violating_after_all_retries() -> None:
    bad = _message(tool_calls=[_tool_call("call_1", "proposer_plats", VIOLATING_PLATS_ARGS)])
    with patch(
        "app.agent.loop.client.complete_with_tools", return_value=bad
    ) as mock_complete:
        result = _run(allergies=PEANUT_ALLERGY)

    assert isinstance(result, loop.PlatsProposed)
    assert result.suggestions == []
    assert result.notes_generales is not None
    assert "Peanut satay" in result.notes_generales
    assert mock_complete.call_count == loop.MAX_ATTEMPTS


def test_loop_keeps_safe_dishes_and_drops_only_the_violating_one() -> None:
    bad = _message(tool_calls=[_tool_call("call_1", "proposer_plats", MIXED_PLATS_ARGS)])
    with patch("app.agent.loop.client.complete_with_tools", return_value=bad):
        result = _run(allergies=PEANUT_ALLERGY)

    assert isinstance(result, loop.PlatsProposed)
    dish_names = [s.dish_name for s in result.suggestions]
    assert dish_names == ["Carrot soup"]
    assert "Peanut satay" in (result.notes_generales or "")


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
