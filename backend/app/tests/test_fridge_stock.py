import json
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

# `starlette.testclient.TestClient` is built on `httpx2.Client` (its own
# successor to `httpx`, see `starlette.testclient`'s import), so that's the
# actual runtime — and static — type of what `client.post(...)` returns
# below, not `httpx.Response`.
from httpx2 import Response

from app.agent.duplicate_check import DuplicateGroupArgs
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


def _add(client: TestClient, name: str, **kwargs: object) -> dict[str, Any]:
    body: dict[str, object] = {"ingredient_name": name, **kwargs}
    response = client.post("/api/fridge-stock", json=body)
    assert response.status_code == 201
    result: dict[str, Any] = response.json()
    return result


def test_merge_suggestions_returns_a_suggestion_for_two_seeded_items(client: TestClient) -> None:
    carottes = _add(client, "carottes", quantity_value=3, quantity_unit="pcs")
    carrots = _add(client, "carrots", quantity_value=2, quantity_unit="pcs")

    groups = [DuplicateGroupArgs(names=["carottes", "carrots"], suggested_name="carottes")]
    with patch(
        "app.services.fridge_stock_service.duplicate_check.find_duplicate_groups",
        return_value=groups,
    ):
        response = client.get("/api/fridge-stock/merge-suggestions")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    ids = {body[0]["item_a"]["id"], body[0]["item_b"]["id"]}
    assert ids == {carottes["id"], carrots["id"]}
    assert body[0]["suggested_name"] == "carottes"


def test_merge_suggestions_drops_a_one_name_group(client: TestClient) -> None:
    # Regression test: a "group" naming only one ingredient (a real
    # possibility — see test_duplicate_check.py) must not produce a
    # bogus self-merge suggestion or crash.
    _add(client, "pommes de terre")
    _add(client, "carottes")
    _add(client, "carrots")

    groups = [
        DuplicateGroupArgs(names=["pommes de terre"], suggested_name="pommes de terre"),
        DuplicateGroupArgs(names=["carottes", "carrots"], suggested_name="carottes"),
    ]
    with patch(
        "app.services.fridge_stock_service.duplicate_check.find_duplicate_groups",
        return_value=groups,
    ):
        response = client.get("/api/fridge-stock/merge-suggestions")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert {body[0]["item_a"]["ingredient_name"], body[0]["item_b"]["ingredient_name"]} == {
        "carottes",
        "carrots",
    }


def test_merge_suggestions_drops_a_group_with_an_unresolvable_name(client: TestClient) -> None:
    _add(client, "carottes")
    _add(client, "lait")

    # "carrots" was never a real item — a hallucinated/rephrased name.
    groups = [DuplicateGroupArgs(names=["carottes", "carrots"], suggested_name="carottes")]
    with patch(
        "app.services.fridge_stock_service.duplicate_check.find_duplicate_groups",
        return_value=groups,
    ):
        response = client.get("/api/fridge-stock/merge-suggestions")

    assert response.status_code == 200
    assert response.json() == []


def test_merge_suggestions_excludes_a_dismissed_pair(client: TestClient) -> None:
    _add(client, "carottes")
    _add(client, "carrots")

    groups = [DuplicateGroupArgs(names=["carottes", "carrots"], suggested_name="carottes")]
    with patch(
        "app.services.fridge_stock_service.duplicate_check.find_duplicate_groups",
        return_value=groups,
    ):
        dismissed = client.post(
            "/api/fridge-stock/merge-suggestions/dismiss",
            json={"name_a": "carottes", "name_b": "carrots"},
        )
        assert dismissed.status_code == 204

        response = client.get("/api/fridge-stock/merge-suggestions")

    assert response.status_code == 200
    assert response.json() == []


def test_merge_sums_quantity_when_units_match(client: TestClient) -> None:
    keep = _add(client, "carottes", quantity_value=3, quantity_unit="pcs")
    remove = _add(client, "carrots", quantity_value=2, quantity_unit="pcs")

    response = client.post(
        "/api/fridge-stock/merge",
        json={
            "keep_item_id": keep["id"],
            "remove_item_id": remove["id"],
            "merged_name": "carottes",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == keep["id"]
    assert body["ingredient_name"] == "carottes"
    # Always lands in `quantity_raw` — see `merge_items()`'s docstring for
    # why (`quantity_value`/`quantity_unit` aren't read anywhere in
    # `pages/Fridge.tsx`, only `quantity_raw` is).
    assert body["quantity_value"] is None
    assert body["quantity_unit"] is None
    assert body["quantity_raw"] == "5 pcs"

    remaining = client.get("/api/fridge-stock").json()
    assert [i["id"] for i in remaining] == [keep["id"]]


def test_merge_sums_raw_quantities_of_the_same_unit(client: TestClient) -> None:
    # The realistic case: the manual add/edit form (`pages/Fridge.tsx`)
    # only ever sets `quantity_raw`, never `quantity_value`/`quantity_unit`
    # — this is the exact scenario that used to lose stock on merge ("1kg"
    # + "6kg" merging down to just "1kg" instead of totaling 7kg).
    keep = _add(client, "carottes", quantity_raw="1kg")
    remove = _add(client, "carrots", quantity_raw="6kg")

    response = client.post(
        "/api/fridge-stock/merge",
        json={
            "keep_item_id": keep["id"],
            "remove_item_id": remove["id"],
            "merged_name": "carottes",
        },
    )

    assert response.status_code == 200
    assert response.json()["quantity_raw"] == "7 kg"


def test_merge_converts_between_compatible_units_before_summing(client: TestClient) -> None:
    keep = _add(client, "carottes", quantity_raw="1kg")
    remove = _add(client, "carrots", quantity_raw="500G")  # mixed case, grams not kg

    response = client.post(
        "/api/fridge-stock/merge",
        json={
            "keep_item_id": keep["id"],
            "remove_item_id": remove["id"],
            "merged_name": "carottes",
        },
    )

    assert response.status_code == 200
    # Expressed in `keep`'s own unit (kg) — 500g converts to 0.5kg first.
    assert response.json()["quantity_raw"] == "1.5 kg"


def test_merge_combines_both_quantities_as_text_when_units_are_not_comparable(
    client: TestClient,
) -> None:
    keep = _add(client, "carottes", quantity_value=2, quantity_unit="kg")
    remove = _add(client, "carrots", quantity_value=3, quantity_unit="pcs")

    response = client.post(
        "/api/fridge-stock/merge",
        json={
            "keep_item_id": keep["id"],
            "remove_item_id": remove["id"],
            "merged_name": "carottes",
        },
    )

    assert response.status_code == 200
    body = response.json()
    # kg and a bare count aren't the same kind of unit — can't be summed
    # into one number without guessing a conversion — but neither amount
    # is allowed to just vanish either (regression test: a merge used to
    # silently keep only `keep`'s quantity and drop `remove`'s entirely).
    assert body["quantity_value"] is None
    assert body["quantity_unit"] is None
    assert body["quantity_raw"] == "2 kg + 3 pcs"


def test_merge_falls_back_to_text_when_a_quantity_is_too_vague_to_parse(
    client: TestClient,
) -> None:
    keep = _add(client, "carottes", quantity_raw="1kg")
    remove = _add(client, "carrots", quantity_raw="about 2kg")

    response = client.post(
        "/api/fridge-stock/merge",
        json={
            "keep_item_id": keep["id"],
            "remove_item_id": remove["id"],
            "merged_name": "carottes",
        },
    )

    assert response.status_code == 200
    assert response.json()["quantity_raw"] == "1kg + about 2kg"


def test_merge_keeps_the_only_known_quantity_when_the_other_side_has_none(
    client: TestClient,
) -> None:
    keep = _add(client, "carottes", quantity_raw="1kg")
    remove = _add(client, "carrots")

    response = client.post(
        "/api/fridge-stock/merge",
        json={
            "keep_item_id": keep["id"],
            "remove_item_id": remove["id"],
            "merged_name": "carottes",
        },
    )

    assert response.status_code == 200
    assert response.json()["quantity_raw"] == "1kg"


def test_merge_with_unknown_id_returns_404(client: TestClient) -> None:
    keep = _add(client, "carottes")

    response = client.post(
        "/api/fridge-stock/merge",
        json={"keep_item_id": keep["id"], "remove_item_id": 999, "merged_name": "carottes"},
    )

    assert response.status_code == 404


def test_merge_with_equal_ids_returns_422(client: TestClient) -> None:
    keep = _add(client, "carottes")

    response = client.post(
        "/api/fridge-stock/merge",
        json={
            "keep_item_id": keep["id"],
            "remove_item_id": keep["id"],
            "merged_name": "carottes",
        },
    )

    assert response.status_code == 422
