from fastapi.testclient import TestClient

PASSWORD = "correct horse battery staple"


def _onboard(client: TestClient) -> None:
    client.post(
        "/api/onboarding",
        json={"default_servings": 4, "allergies": [], "preference_notes": []},
    )


def test_auth_status_initially_not_set(client: TestClient) -> None:
    response = client.get("/api/auth/status")

    assert response.status_code == 200
    assert response.json() == {"password_set": False, "unlocked": False}


def test_setup_password_unlocks_immediately(client: TestClient) -> None:
    response = client.post("/api/auth/setup", json={"password": PASSWORD})

    assert response.status_code == 204
    assert client.get("/api/auth/status").json() == {"password_set": True, "unlocked": True}


def test_setup_password_twice_is_rejected(client: TestClient) -> None:
    client.post("/api/auth/setup", json={"password": PASSWORD})

    response = client.post("/api/auth/setup", json={"password": "another password entirely"})

    assert response.status_code == 409


def test_setup_password_too_short_is_rejected(client: TestClient) -> None:
    response = client.post("/api/auth/setup", json={"password": "short"})

    assert response.status_code == 422


def test_lock_then_unlock_with_correct_password(client: TestClient) -> None:
    client.post("/api/auth/setup", json={"password": PASSWORD})
    client.post("/api/auth/lock")
    assert client.get("/api/auth/status").json()["unlocked"] is False

    response = client.post("/api/auth/unlock", json={"password": PASSWORD})

    assert response.status_code == 204
    assert client.get("/api/auth/status").json()["unlocked"] is True


def test_unlock_with_wrong_password_is_rejected(client: TestClient) -> None:
    client.post("/api/auth/setup", json={"password": PASSWORD})
    client.post("/api/auth/lock")

    response = client.post("/api/auth/unlock", json={"password": "wrong password"})

    assert response.status_code == 401
    assert client.get("/api/auth/status").json()["unlocked"] is False


def test_unlock_before_any_password_set_is_rejected(client: TestClient) -> None:
    response = client.post("/api/auth/unlock", json={"password": "anything"})

    assert response.status_code == 401


def test_set_token_requires_unlocked_vault(client: TestClient) -> None:
    response = client.post("/api/auth/token", json={"token": "sk-or-v1-secret"})

    assert response.status_code == 423


def test_set_token_after_password_setup_is_reflected_in_settings(client: TestClient) -> None:
    client.post("/api/auth/setup", json={"password": PASSWORD})

    response = client.post("/api/auth/token", json={"token": "sk-or-v1-secret"})
    assert response.status_code == 204

    _onboard(client)
    assert client.get("/api/settings").json()["openrouter_token_configured"] is True


def test_set_token_survives_lock_and_unlock(client: TestClient) -> None:
    client.post("/api/auth/setup", json={"password": PASSWORD})
    client.post("/api/auth/token", json={"token": "sk-or-v1-secret"})
    _onboard(client)

    client.post("/api/auth/lock")
    # Configured status is readable even locked — it's a plain boolean on
    # the entity, no decryption needed.
    assert client.get("/api/settings").json()["openrouter_token_configured"] is True

    client.post("/api/auth/unlock", json={"password": PASSWORD})
    assert client.get("/api/settings").json()["openrouter_token_configured"] is True
