from fastapi.testclient import TestClient


def test_onboarding_status_false_before_onboarding(client: TestClient) -> None:
    response = client.get("/api/onboarding/status")

    assert response.status_code == 200
    assert response.json() == {"onboarded": False}


def test_complete_onboarding_creates_settings_and_seeds_allergies_and_preferences(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/onboarding",
        json={
            "default_servings": 4,
            "allergies": ["peanut", "shellfish"],
            "preference_notes": ["loves spicy food"],
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "default_servings": 4,
        "openrouter_model_id": None,
        "openrouter_token_configured": False,
    }

    assert client.get("/api/onboarding/status").json() == {"onboarded": True}

    allergies = client.get("/api/allergies").json()
    assert {a["ingredient_name"] for a in allergies} == {"peanut", "shellfish"}

    preferences = client.get("/api/preferences").json()
    assert len(preferences) == 1
    assert preferences[0]["content"] == "loves spicy food"
    assert preferences[0]["source"] == "onboarding"


def test_complete_onboarding_bundles_chosen_model_id(client: TestClient) -> None:
    response = client.post(
        "/api/onboarding",
        json={
            "default_servings": 4,
            "allergies": [],
            "preference_notes": [],
            "openrouter_model_id": "foo/bar:free",
        },
    )

    assert response.status_code == 201
    assert response.json()["openrouter_model_id"] == "foo/bar:free"


def test_onboarding_twice_is_rejected(client: TestClient) -> None:
    payload = {"default_servings": 4, "allergies": [], "preference_notes": []}
    client.post("/api/onboarding", json=payload)

    response = client.post("/api/onboarding", json=payload)

    assert response.status_code == 409


def test_onboarding_rejects_non_positive_servings(client: TestClient) -> None:
    response = client.post(
        "/api/onboarding",
        json={"default_servings": 0, "allergies": [], "preference_notes": []},
    )

    assert response.status_code == 422
