from fastapi.testclient import TestClient


def _onboard(client: TestClient, default_servings: int = 4) -> None:
    client.post(
        "/api/onboarding",
        json={"default_servings": default_servings, "allergies": [], "preference_notes": []},
    )


def test_get_settings_before_onboarding_is_conflict(client: TestClient) -> None:
    response = client.get("/api/settings")

    assert response.status_code == 409


def test_update_settings_changes_default_servings(client: TestClient) -> None:
    _onboard(client, default_servings=4)

    response = client.patch("/api/settings", json={"default_servings": 6})

    assert response.status_code == 200
    assert response.json()["default_servings"] == 6
    assert client.get("/api/settings").json()["default_servings"] == 6
