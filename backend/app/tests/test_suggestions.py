from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agent import loop
from app.domain.dish_idea import DishIdea
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


def _ideas_proposed() -> loop.IdeasProposed:
    return loop.IdeasProposed(
        ideas=[
            DishIdea(dish_name="Carrot soup", description="Simple soup"),
            DishIdea(dish_name="Tomato soup", description="Another soup"),
        ],
        notes_generales="Pick one!",
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
                        "function": {"name": "proposer_idees", "arguments": "{}"},
                    }
                ],
            },
        ],
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


def test_create_suggestions_requires_days_in_batch_mode(client: TestClient) -> None:
    response = client.post(
        "/api/suggestions",
        json={"mode": "batch", "items": [{"ingredient_name": "egg"}]},
    )

    assert response.status_code == 422


def test_create_suggestions_ignores_days_in_single_mode(client: TestClient) -> None:
    _setup(client)

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch("app.services.suggestion_service.loop.run_ideas", return_value=_ideas_proposed()),
    ):
        response = client.post(
            "/api/suggestions",
            json={"mode": "single", "items": [{"ingredient_name": "egg"}]},
        )

    assert response.status_code == 200


# --- IDEAS phase (setup + mocked loop — no live LLM call in tests) ---


def test_create_suggestions_returns_ideas_proposed_result(client: TestClient) -> None:
    _setup(client)

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch("app.services.suggestion_service.loop.run_ideas", return_value=_ideas_proposed()),
    ):
        response = client.post(
            "/api/suggestions",
            json={
                "mode": "batch",
                "days": 5,
                "items": [{"ingredient_name": "carrot", "quantity_raw": "3"}],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ideas_proposed"
    assert isinstance(body["fridge_input_id"], int)
    assert isinstance(body["run_id"], int)
    assert body["ideas"] == [
        {"index": 0, "dish_name": "Carrot soup", "description": "Simple soup"},
        {"index": 1, "dish_name": "Tomato soup", "description": "Another soup"},
    ]
    assert body["notes_generales"] == "Pick one!"
    assert body["suggestions"] == []


def test_create_suggestions_defaults_to_batch_mode(client: TestClient) -> None:
    _setup(client)

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch("app.services.suggestion_service.loop.run_ideas", return_value=_ideas_proposed()),
    ):
        response = client.post(
            "/api/suggestions", json={"days": 5, "items": [{"ingredient_name": "egg"}]}
        )

    assert response.status_code == 200


def test_create_suggestions_returns_clarification_needed(client: TestClient) -> None:
    _setup(client)

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch("app.services.suggestion_service.loop.run_ideas", return_value=_clarification()),
    ):
        response = client.post(
            "/api/suggestions",
            json={"mode": "batch", "days": 5, "items": [{"ingredient_name": "carrot"}]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "clarification_needed"
    assert body["question"] == "How many people?"
    assert body["options"] == ["2", "4"]
    assert isinstance(body["run_id"], int)
    assert body["suggestions"] == []
    assert body["ideas"] == []


def test_respond_resumes_ideas_phase_clarification(client: TestClient) -> None:
    _setup(client)
    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch("app.services.suggestion_service.loop.run_ideas", return_value=_clarification()),
    ):
        first = client.post(
            "/api/suggestions",
            json={"mode": "batch", "days": 5, "items": [{"ingredient_name": "carrot"}]},
        )
    run_id = first.json()["run_id"]

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch(
            "app.services.suggestion_service.loop.run_ideas", return_value=_ideas_proposed()
        ) as mock_run_ideas,
    ):
        response = client.post(
            f"/api/suggestions/runs/{run_id}/respond", json={"answer": "4 people"}
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ideas_proposed"
    sent_messages = mock_run_ideas.call_args.kwargs["messages"]
    assert sent_messages[-1] == {"role": "tool", "tool_call_id": "call_1", "content": "4 people"}


def test_respond_with_unknown_run_id_returns_404(client: TestClient) -> None:
    _setup(client)

    response = client.post("/api/suggestions/runs/999/respond", json={"answer": "4 people"})

    assert response.status_code == 404


def test_create_suggestions_requires_vault_unlocked(client: TestClient) -> None:
    _setup(client)
    client.post("/api/auth/lock")

    response = client.post(
        "/api/suggestions",
        json={"mode": "batch", "days": 5, "items": [{"ingredient_name": "carrot"}]},
    )

    assert response.status_code == 423


def test_create_suggestions_requires_model_configured(client: TestClient) -> None:
    _setup(client, with_model=False)

    response = client.post(
        "/api/suggestions",
        json={"mode": "batch", "days": 5, "items": [{"ingredient_name": "carrot"}]},
    )

    assert response.status_code == 409


def test_create_suggestions_returns_409_when_model_no_longer_available(
    client: TestClient,
) -> None:
    _setup(client)

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=False),
        patch("app.services.suggestion_service.loop.run_ideas") as mock_run_ideas,
    ):
        response = client.post(
            "/api/suggestions",
            json={"mode": "batch", "days": 5, "items": [{"ingredient_name": "carrot"}]},
        )

    assert response.status_code == 409
    mock_run_ideas.assert_not_called()


# --- Selection -> RECIPES phase ---


def _propose_ideas(client: TestClient) -> str:
    _setup(client)
    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch("app.services.suggestion_service.loop.run_ideas", return_value=_ideas_proposed()),
    ):
        response = client.post(
            "/api/suggestions",
            json={
                "mode": "batch",
                "days": 5,
                "items": [{"ingredient_name": "carrot", "quantity_raw": "3"}],
            },
        )
    return str(response.json()["run_id"])


def test_select_returns_completed_result_and_persists_the_meal_plan(client: TestClient) -> None:
    run_id = _propose_ideas(client)

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch(
            "app.services.suggestion_service.loop.run", return_value=_plats_proposed()
        ) as mock_run,
    ):
        response = client.post(
            f"/api/suggestions/runs/{run_id}/select", json={"selected_indexes": [0]}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["suggestions"][0]["dish_name"] == "Carrot soup"
    assert mock_run.call_args.kwargs["selected_dish_names"] == ["Carrot soup"]
    sent_messages = mock_run.call_args.kwargs["messages"]
    tool_feedback = [m["content"] for m in sent_messages if m.get("role") == "tool"]
    assert any(fb and "Carrot soup" in fb for fb in tool_feedback)

    meal_plan_id = body["meal_plan_id"]
    detail = client.get(f"/api/meal-plans/{meal_plan_id}")
    assert detail.status_code == 200
    assert detail.json()["mode"] == "batch"
    assert detail.json()["suggestions"][0]["dish_name"] == "Carrot soup"

    listing = client.get("/api/meal-plans")
    assert listing.status_code == 200
    assert [p["id"] for p in listing.json()] == [meal_plan_id]


def test_select_with_unknown_run_id_returns_404(client: TestClient) -> None:
    _setup(client)

    response = client.post("/api/suggestions/runs/999/select", json={"selected_indexes": [0]})

    assert response.status_code == 404


def test_select_with_out_of_range_index_returns_404(client: TestClient) -> None:
    run_id = _propose_ideas(client)

    response = client.post(
        f"/api/suggestions/runs/{run_id}/select", json={"selected_indexes": [5]}
    )

    assert response.status_code == 404


def test_respond_resumes_recipes_phase_clarification(client: TestClient) -> None:
    run_id = _propose_ideas(client)

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch("app.services.suggestion_service.loop.run", return_value=_clarification()),
    ):
        selected = client.post(
            f"/api/suggestions/runs/{run_id}/select", json={"selected_indexes": [0]}
        )
    assert selected.status_code == 200
    assert selected.json()["status"] == "clarification_needed"
    recipe_run_id = selected.json()["run_id"]
    # `select()` resumes the same AgentRun row rather than creating a new one.
    assert str(recipe_run_id) == run_id

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch(
            "app.services.suggestion_service.loop.run", return_value=_plats_proposed()
        ) as mock_run,
    ):
        response = client.post(
            f"/api/suggestions/runs/{recipe_run_id}/respond", json={"answer": "yes, that's fine"}
        )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert mock_run.call_args.kwargs["selected_dish_names"] == ["Carrot soup"]


def _plats_proposed_using_stock(stock_id: int) -> loop.PlatsProposed:
    result = _plats_proposed()
    result.suggestions[0].used_stock_item_ids_json = f"[{stock_id}]"
    return result


def test_select_deducts_reported_stock_items_from_the_fridge(client: TestClient) -> None:
    _setup(client)
    stock_item = client.post(
        "/api/fridge-stock", json={"ingredient_name": "carrot", "quantity_raw": "3"}
    ).json()
    stock_id = stock_item["id"]

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch("app.services.suggestion_service.loop.run_ideas", return_value=_ideas_proposed()),
    ):
        propose_response = client.post(
            "/api/suggestions",
            json={
                "mode": "batch",
                "days": 5,
                "items": [
                    {
                        "ingredient_name": "carrot",
                        "quantity_raw": "3",
                        "fridge_stock_item_id": stock_id,
                    }
                ],
            },
        )
    run_id = propose_response.json()["run_id"]

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch(
            "app.services.suggestion_service.loop.run",
            return_value=_plats_proposed_using_stock(stock_id),
        ) as mock_run,
    ):
        response = client.post(
            f"/api/suggestions/runs/{run_id}/select", json={"selected_indexes": [0]}
        )

    assert mock_run.call_args.kwargs["known_stock_item_ids"] == {stock_id}

    body = response.json()
    assert [item["id"] for item in body["removed_stock_items"]] == [stock_id]

    remaining = client.get("/api/fridge-stock").json()
    assert remaining == []


def test_select_does_not_deduct_stock_items_the_recipe_did_not_report_using(
    client: TestClient,
) -> None:
    _setup(client)
    stock_item = client.post(
        "/api/fridge-stock", json={"ingredient_name": "carrot", "quantity_raw": "3"}
    ).json()
    stock_id = stock_item["id"]

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch("app.services.suggestion_service.loop.run_ideas", return_value=_ideas_proposed()),
    ):
        propose_response = client.post(
            "/api/suggestions",
            json={
                "mode": "batch",
                "days": 5,
                "items": [
                    {
                        "ingredient_name": "carrot",
                        "quantity_raw": "3",
                        "fridge_stock_item_id": stock_id,
                    }
                ],
            },
        )
    run_id = propose_response.json()["run_id"]

    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch("app.services.suggestion_service.loop.run", return_value=_plats_proposed()),
    ):
        response = client.post(
            f"/api/suggestions/runs/{run_id}/select", json={"selected_indexes": [0]}
        )

    assert response.json()["removed_stock_items"] == []
    remaining = client.get("/api/fridge-stock").json()
    assert [item["id"] for item in remaining] == [stock_id]
