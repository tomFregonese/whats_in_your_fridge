from fastapi.testclient import TestClient


def test_create_suggestions_with_items_only(client: TestClient) -> None:
    response = client.post(
        "/api/suggestions",
        json={
            "mode": "batch",
            "items": [{"ingredient_name": "carrot", "quantity_raw": "3"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert isinstance(body["fridge_input_id"], int)
    assert len(body["suggestions"]) > 0
    first = body["suggestions"][0]
    assert set(first.keys()) == {"dish_name", "description", "ingredients", "steps", "servings"}
    assert isinstance(first["ingredients"], list)
    assert isinstance(first["steps"], list)


def test_create_suggestions_with_free_text_only(client: TestClient) -> None:
    response = client.post(
        "/api/suggestions",
        json={"mode": "single", "free_text": "half a lemon and some leftover rice"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_create_suggestions_requires_items_or_free_text(client: TestClient) -> None:
    response = client.post("/api/suggestions", json={"mode": "batch"})

    assert response.status_code == 422


def test_create_suggestions_rejects_blank_free_text_with_no_items(client: TestClient) -> None:
    response = client.post("/api/suggestions", json={"mode": "batch", "free_text": "   "})

    assert response.status_code == 422


def test_create_suggestions_defaults_to_batch_mode(client: TestClient) -> None:
    response = client.post(
        "/api/suggestions",
        json={"items": [{"ingredient_name": "egg"}]},
    )

    assert response.status_code == 200


def test_create_suggestions_rejects_unknown_mode(client: TestClient) -> None:
    response = client.post(
        "/api/suggestions",
        json={"mode": "weekly", "items": [{"ingredient_name": "egg"}]},
    )

    assert response.status_code == 422
