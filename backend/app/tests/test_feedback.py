from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agent import loop
from app.domain.suggestion import AllergyCheckStatus, Suggestion

PASSWORD = "correct horse battery staple"


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


def _create_suggestion(client: TestClient, dish_name: str = "Carrot soup") -> int:
    """Runs the real (mocked-loop) generation flow to get a real, persisted
    suggestion id — feedback always targets a real `suggestion.id`.
    """
    plats = loop.PlatsProposed(
        suggestions=[
            Suggestion(
                id=None,
                meal_plan_id=None,
                dish_name=dish_name,
                description="Simple soup",
                ingredients_json='["carrot (3)"]',
                steps_json='["Boil.", "Blend."]',
                servings=4,
                allergy_check_status=AllergyCheckStatus.OK,
            )
        ],
        notes_generales=None,
    )
    with (
        patch("app.services.suggestion_service.is_model_available", return_value=True),
        patch("app.services.suggestion_service.loop.run", return_value=plats),
    ):
        response = client.post(
            "/api/suggestions",
            json={"mode": "batch", "items": [{"ingredient_name": "carrot"}]},
        )
    suggestion_id: int = response.json()["suggestions"][0]["id"]
    return suggestion_id


def test_add_feedback_requires_liked_or_comment(client: TestClient) -> None:
    _setup(client)
    suggestion_id = _create_suggestion(client)

    response = client.post(f"/api/suggestions/{suggestion_id}/feedback", json={})

    assert response.status_code == 422


def test_add_feedback_for_unknown_suggestion_returns_404(client: TestClient) -> None:
    response = client.post("/api/suggestions/999/feedback", json={"liked": True})

    assert response.status_code == 404


def test_add_feedback_with_thumbs_up_only(client: TestClient) -> None:
    _setup(client)
    suggestion_id = _create_suggestion(client)

    response = client.post(f"/api/suggestions/{suggestion_id}/feedback", json={"liked": True})

    assert response.status_code == 201
    body = response.json()
    assert body["suggestion_id"] == suggestion_id
    assert body["liked"] is True
    assert body["comment"] is None


def test_add_feedback_with_comment_only(client: TestClient) -> None:
    _setup(client)
    suggestion_id = _create_suggestion(client)

    response = client.post(
        f"/api/suggestions/{suggestion_id}/feedback", json={"comment": "Too bland"}
    )

    assert response.status_code == 201
    assert response.json()["liked"] is None
    assert response.json()["comment"] == "Too bland"


def test_resubmitting_feedback_updates_the_same_row(client: TestClient) -> None:
    _setup(client)
    suggestion_id = _create_suggestion(client)

    first = client.post(f"/api/suggestions/{suggestion_id}/feedback", json={"liked": True})
    second = client.post(
        f"/api/suggestions/{suggestion_id}/feedback",
        json={"liked": False, "comment": "Changed my mind"},
    )

    assert first.json()["id"] == second.json()["id"]
    assert second.json()["liked"] is False
    assert second.json()["comment"] == "Changed my mind"


def test_feedback_comment_becomes_a_preference_note(client: TestClient) -> None:
    _setup(client)
    suggestion_id = _create_suggestion(client, dish_name="Carrot soup")

    client.post(
        f"/api/suggestions/{suggestion_id}/feedback",
        json={"liked": False, "comment": "Too salty"},
    )

    notes = client.get("/api/preferences").json()
    feedback_notes = [n for n in notes if n["source"] == "feedback"]
    assert len(feedback_notes) == 1
    assert feedback_notes[0]["content"] == 'Disliked "Carrot soup": Too salty'


def test_feedback_without_comment_does_not_create_a_preference_note(client: TestClient) -> None:
    _setup(client)
    suggestion_id = _create_suggestion(client)

    client.post(f"/api/suggestions/{suggestion_id}/feedback", json={"liked": True})

    notes = client.get("/api/preferences").json()
    assert [n for n in notes if n["source"] == "feedback"] == []


def test_feedback_blank_comment_does_not_create_a_preference_note(client: TestClient) -> None:
    _setup(client)
    suggestion_id = _create_suggestion(client)

    client.post(
        f"/api/suggestions/{suggestion_id}/feedback", json={"liked": True, "comment": "   "}
    )

    notes = client.get("/api/preferences").json()
    assert [n for n in notes if n["source"] == "feedback"] == []
