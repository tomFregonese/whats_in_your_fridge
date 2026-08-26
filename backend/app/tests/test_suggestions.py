from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agent import loop
from app.domain.suggestion import AllergyCheckStatus, Suggestion

PASSWORD = "correct horse battery staple"


def _setup(client: TestClient, *, with_model: bool = True) -> None:
    client.post("/api/auth/setup", json={"password": PASSWORD})
    client.post("/api/auth/token", json={"token": "sk-or-v1-fake"})
    client.post(
        "/api/onboarding",
        json={
            "default_servings": 4,
            "allergies": [],
            "preference_notes": [],
            **({"openrouter_model_id": "some/model:free"} if with_model else {}),
        },
    )


def _plats_proposed() -> loop.PlatsProposed:
    return loop.PlatsProposed(
        suggestions=[
            Suggestion(
                id=None,
                meal_plan_id=None,
                dish_name="Carrot soup",
                description="Simple soup",
                ingredients_json='["carrot (3)"]',
                steps_json='["Boil.", "Blend."]',
                servings=4,
                allergy_check_status=AllergyCheckStatus.OK,
            )
        ],
        notes_generales="Enjoy!",
    )


def _clarification() -> loop.ClarificationNeeded:
    return loop.ClarificationNeeded(
        question="How many people?",
        options=["2", "4"],
        messages=[
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "demander_precision", "arguments": "{}"},
                    }
                ],
            },
        ],
    )


# --- Dto validation (no setup needed — fails before the service runs) ---


def test_create_suggestions_requires_items_or_free_text(client: TestClient) -> None:
    response = client.post("/api/suggestions", json={"mode": "batch"})

    assert response.status_code == 422


def test_create_suggestions_rejects_blank_free_text_with_no_items(client: TestClient) -> None:
    response = client.post("/api/suggestions", json={"mode": "batch", "free_text": "   "})

    assert response.status_code == 422


def test_create_suggestions_rejects_unknown_mode(client: TestClient) -> None:
    response = client.post(
        "/api/suggestions",
        json={"mode": "weekly", "items": [{"ingredient_name": "egg"}]},
    )

    assert response.status_code == 422


# --- Real flow (setup + mocked loop — no live LLM call in tests) ---


def test_create_suggestions_returns_completed_result(client: TestClient) -> None:
    _setup(client)

    with patch("app.services.suggestion_service.loop.run", return_value=_plats_proposed()):
        response = client.post(
            "/api/suggestions",
            json={"mode": "batch", "items": [{"ingredient_name": "carrot", "quantity_raw": "3"}]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert isinstance(body["fridge_input_id"], int)
    assert body["suggestions"][0]["dish_name"] == "Carrot soup"
    assert body["notes_generales"] == "Enjoy!"


def test_create_suggestions_defaults_to_batch_mode(client: TestClient) -> None:
    _setup(client)

    with patch("app.services.suggestion_service.loop.run", return_value=_plats_proposed()):
        response = client.post("/api/suggestions", json={"items": [{"ingredient_name": "egg"}]})

    assert response.status_code == 200


def test_create_suggestions_returns_clarification_needed(client: TestClient) -> None:
    _setup(client)

    with patch("app.services.suggestion_service.loop.run", return_value=_clarification()):
        response = client.post(
            "/api/suggestions", json={"mode": "batch", "items": [{"ingredient_name": "carrot"}]}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "clarification_needed"
    assert body["question"] == "How many people?"
    assert body["options"] == ["2", "4"]
    assert isinstance(body["run_id"], int)
    assert body["suggestions"] == []


def test_respond_continues_the_conversation_and_appends_the_answer(client: TestClient) -> None:
    _setup(client)
    with patch("app.services.suggestion_service.loop.run", return_value=_clarification()):
        first = client.post(
            "/api/suggestions", json={"mode": "batch", "items": [{"ingredient_name": "carrot"}]}
        )
    run_id = first.json()["run_id"]

    with patch(
        "app.services.suggestion_service.loop.run", return_value=_plats_proposed()
    ) as mock_run:
        response = client.post(
            f"/api/suggestions/runs/{run_id}/respond", json={"answer": "4 people"}
        )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    sent_messages = mock_run.call_args.kwargs["messages"]
    assert sent_messages[-1] == {"role": "tool", "tool_call_id": "call_1", "content": "4 people"}


def test_respond_with_unknown_run_id_returns_404(client: TestClient) -> None:
    _setup(client)

    response = client.post("/api/suggestions/runs/999/respond", json={"answer": "4 people"})

    assert response.status_code == 404


def test_create_suggestions_requires_vault_unlocked(client: TestClient) -> None:
    _setup(client)
    client.post("/api/auth/lock")

    response = client.post(
        "/api/suggestions", json={"mode": "batch", "items": [{"ingredient_name": "carrot"}]}
    )

    assert response.status_code == 423


def test_create_suggestions_requires_model_configured(client: TestClient) -> None:
    _setup(client, with_model=False)

    response = client.post(
        "/api/suggestions", json={"mode": "batch", "items": [{"ingredient_name": "carrot"}]}
    )

    assert response.status_code == 409
