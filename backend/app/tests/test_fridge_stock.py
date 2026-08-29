import json
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from httpx import Response

from app.agent.output_schema import DictatedItemArgs
from app.services.exceptions import NlpUnavailableError, SttUnavailableError

PASSWORD = "correct horse battery staple"


def _sse_events(response: Response) -> list[dict[str, Any]]:
    """Parses a `text/event-stream` response body (a full response, not a
    live connection — `TestClient` drives the ASGI app to completion
    in-process) into the list of `data: ...` JSON payloads it carried."""
    events: list[dict[str, Any]] = []
    for line in response.text.split("\n\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


def _setup(client: TestClient) -> None:
    client.post("/api/auth/setup", json={"password": PASSWORD})
    client.post("/api/auth/token", json={"token": "sk-or-v1-fake"})
    client.post(
        "/api/onboarding",
        json={
            "default_servings": 4,
            "allergies": [],
            "preference_notes": [],
            "openrouter_model_id": "some/model:free",
        },
    )


def test_add_list_update_and_delete_fridge_stock_item(client: TestClient) -> None:
    created = client.post(
        "/api/fridge-stock",
        json={"ingredient_name": "carrot", "quantity_value": 3, "quantity_unit": "pcs"},
    )
    assert created.status_code == 201
    item_id = created.json()["id"]

    listed = client.get("/api/fridge-stock").json()
    assert [i["ingredient_name"] for i in listed] == ["carrot"]

    updated = client.patch(
        f"/api/fridge-stock/{item_id}",
        json={"ingredient_name": "carrot", "quantity_value": 5, "quantity_unit": "pcs"},
    )
    assert updated.status_code == 200
    assert updated.json()["quantity_value"] == 5

    deleted = client.delete(f"/api/fridge-stock/{item_id}")
    assert deleted.status_code == 204
    assert client.get("/api/fridge-stock").json() == []


def test_update_unknown_fridge_stock_item_returns_404(client: TestClient) -> None:
    response = client.patch(
        "/api/fridge-stock/999", json={"ingredient_name": "carrot"}
    )

    assert response.status_code == 404


def test_delete_unknown_fridge_stock_item_returns_404(client: TestClient) -> None:
    response = client.delete("/api/fridge-stock/999")

    assert response.status_code == 404


def test_dictation_streams_transcribing_then_items_without_persisting(
    client: TestClient,
) -> None:
    _setup(client)
    parsed = [
        DictatedItemArgs(
            ingredient_name="carrot", quantity_value=2, quantity_unit="pcs", quantity_raw=None
        ),
        DictatedItemArgs(
            ingredient_name="milk", quantity_value=None, quantity_unit=None, quantity_raw="a liter"
        ),
    ]

    with (
        patch(
            "app.dictation_streaming_service.stt_client.transcribe",
            return_value="two carrots and a liter of milk",
        ) as mock_transcribe,
        patch(
            "app.dictation_streaming_service.dictation.parse_transcript",
            return_value=parsed,
        ) as mock_parse,
    ):
        response = client.post(
            "/api/fridge-stock/dictation",
            json={"audio_base64": "ZmFrZS1hdWRpby1ieXRlcw==", "audio_format": "wav"},
        )

    assert response.status_code == 200
    events = _sse_events(response)
    assert events[0] == {"type": "transcribing"}
    assert events[1] == {"type": "transcribed", "text": "two carrots and a liter of milk"}
    assert events[2] == {
        "type": "items",
        "items": [
            {
                "ingredient_name": "carrot",
                "quantity_value": 2,
                "quantity_unit": "pcs",
                "quantity_raw": None,
            },
            {
                "ingredient_name": "milk",
                "quantity_value": None,
                "quantity_unit": None,
                "quantity_raw": "a liter",
            },
        ],
    }
    assert events[-1] == {"type": "done"}
    assert mock_transcribe.call_args.kwargs["audio_base64"] == "ZmFrZS1hdWRpby1ieXRlcw=="
    assert mock_transcribe.call_args.kwargs["audio_format"] == "wav"
    assert mock_parse.call_args.kwargs["transcript"] == "two carrots and a liter of milk"
    # Parsing is a preview only — nothing is persisted until `/bulk`.
    assert client.get("/api/fridge-stock").json() == []


def test_dictation_streams_an_error_event_when_the_local_stt_service_is_unreachable(
    client: TestClient,
) -> None:
    _setup(client)

    with patch(
        "app.dictation_streaming_service.stt_client.transcribe",
        side_effect=SttUnavailableError("Could not reach the local speech-to-text service."),
    ):
        response = client.post(
            "/api/fridge-stock/dictation",
            json={"audio_base64": "ZmFrZS1hdWRpby1ieXRlcw==", "audio_format": "wav"},
        )

    # The stream already committed to a 200 before the pipeline failed —
    # unlike a normal (non-streaming) endpoint, the failure surfaces as an
    # `error` event, not an HTTP error status.
    assert response.status_code == 200
    events = _sse_events(response)
    assert events[0] == {"type": "transcribing"}
    assert events[1] == {
        "type": "error",
        "detail": "Could not reach the local speech-to-text service.",
    }
    assert events[-1] == {"type": "done"}


def test_dictation_streams_an_error_event_when_the_local_nlp_service_is_unreachable(
    client: TestClient,
) -> None:
    _setup(client)

    with (
        patch(
            "app.dictation_streaming_service.stt_client.transcribe",
            return_value="carrot",
        ),
        patch(
            "app.dictation_streaming_service.dictation.parse_transcript",
            side_effect=NlpUnavailableError(
                "Could not reach the local structuring service."
            ),
        ),
    ):
        response = client.post(
            "/api/fridge-stock/dictation",
            json={"audio_base64": "ZmFrZS1hdWRpby1ieXRlcw==", "audio_format": "wav"},
        )

    assert response.status_code == 200
    events = _sse_events(response)
    # Transcription succeeded (it's a different service) — only structuring failed.
    assert events[0] == {"type": "transcribing"}
    assert events[1] == {"type": "transcribed", "text": "carrot"}
    assert events[2] == {
        "type": "error",
        "detail": "Could not reach the local structuring service.",
    }
    assert events[-1] == {"type": "done"}


def test_bulk_add_updates_existing_item_by_name_and_adds_new_ones(client: TestClient) -> None:
    existing = client.post(
        "/api/fridge-stock", json={"ingredient_name": "carrot", "quantity_raw": "1"}
    ).json()

    response = client.post(
        "/api/fridge-stock/bulk",
        json={
            "items": [
                {"ingredient_name": "Carrot", "quantity_raw": "5"},
                {"ingredient_name": "milk", "quantity_raw": "1 liter"},
            ]
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 2

    remaining = client.get("/api/fridge-stock").json()
    assert len(remaining) == 2
    carrot = next(i for i in remaining if i["ingredient_name"].lower() == "carrot")
    assert carrot["id"] == existing["id"]
    assert carrot["quantity_raw"] == "5"
    assert any(i["ingredient_name"] == "milk" for i in remaining)
