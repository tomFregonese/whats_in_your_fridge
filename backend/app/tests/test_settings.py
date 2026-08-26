from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

FAKE_PAYLOAD = {
    "data": [
        {"id": "foo/bar:free", "name": "Foo Bar (free)", "context_length": 8192},
        {"id": "foo/baz", "name": "Foo Baz (paid)"},
    ]
}


def _onboard(client: TestClient, default_servings: int = 4) -> None:
    client.post(
        "/api/onboarding",
        json={"default_servings": default_servings, "allergies": [], "preference_notes": []},
    )


def _mock_catalog_response() -> MagicMock:
    response = MagicMock()
    response.json.return_value = FAKE_PAYLOAD
    response.raise_for_status.return_value = None
    return response


def test_get_settings_before_onboarding_is_conflict(client: TestClient) -> None:
    response = client.get("/api/settings")

    assert response.status_code == 409


def test_update_settings_changes_default_servings(client: TestClient) -> None:
    _onboard(client, default_servings=4)

    response = client.patch("/api/settings", json={"default_servings": 6})

    assert response.status_code == 200
    assert response.json()["default_servings"] == 6
    assert client.get("/api/settings").json()["default_servings"] == 6


def test_get_settings_reports_no_token_configured_by_default(client: TestClient) -> None:
    _onboard(client)

    assert client.get("/api/settings").json()["openrouter_token_configured"] is False


def test_update_settings_changes_model_id(client: TestClient) -> None:
    _onboard(client)

    response = client.patch(
        "/api/settings", json={"default_servings": 4, "openrouter_model_id": "foo/bar:free"}
    )

    assert response.status_code == 200
    assert response.json()["openrouter_model_id"] == "foo/bar:free"


def test_update_settings_omitting_model_id_leaves_it_unchanged(client: TestClient) -> None:
    _onboard(client)
    client.patch(
        "/api/settings", json={"default_servings": 4, "openrouter_model_id": "foo/bar:free"}
    )

    response = client.patch("/api/settings", json={"default_servings": 5})

    assert response.json()["default_servings"] == 5
    assert response.json()["openrouter_model_id"] == "foo/bar:free"


def test_list_free_models_filters_and_maps(client: TestClient) -> None:
    with patch("app.agent.catalog.httpx.get", return_value=_mock_catalog_response()):
        response = client.get("/api/settings/models")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "foo/bar:free",
            "name": "Foo Bar (free)",
            "context_length": 8192,
            "description": None,
        }
    ]


def test_model_status_before_onboarding_is_conflict(client: TestClient) -> None:
    response = client.get("/api/settings/model-status")

    assert response.status_code == 409


def test_model_status_reports_no_model_when_none_selected(client: TestClient) -> None:
    _onboard(client)

    with patch("app.agent.catalog.httpx.get", return_value=_mock_catalog_response()):
        response = client.get("/api/settings/model-status")

    assert response.status_code == 200
    assert response.json() == {"model_id": None, "available": False}


def test_model_status_reports_available_when_model_in_catalog(client: TestClient) -> None:
    _onboard(client)
    with patch("app.agent.catalog.httpx.get", return_value=_mock_catalog_response()):
        client.patch(
            "/api/settings", json={"default_servings": 4, "openrouter_model_id": "foo/bar:free"}
        )

        response = client.get("/api/settings/model-status")

    assert response.status_code == 200
    assert response.json() == {"model_id": "foo/bar:free", "available": True}


def test_model_status_reports_unavailable_when_model_dropped_from_catalog(
    client: TestClient,
) -> None:
    _onboard(client)
    with patch("app.agent.catalog.httpx.get", return_value=_mock_catalog_response()):
        client.patch(
            "/api/settings", json={"default_servings": 4, "openrouter_model_id": "foo/bar:free"}
        )

    # Catalog refreshed without `foo/bar:free` anymore (e.g. OpenRouter retired it).
    narrower_payload = {"data": [{"id": "other/model:free", "name": "Other"}]}
    narrower_response = MagicMock()
    narrower_response.json.return_value = narrower_payload
    narrower_response.raise_for_status.return_value = None
    with patch("app.agent.catalog.httpx.get", return_value=narrower_response):
        response = client.get("/api/settings/model-status")

    assert response.status_code == 200
    assert response.json() == {"model_id": "foo/bar:free", "available": False}
