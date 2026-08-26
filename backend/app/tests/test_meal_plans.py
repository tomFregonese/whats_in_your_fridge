from fastapi.testclient import TestClient


def test_list_meal_plans_empty_when_none_persisted(client: TestClient) -> None:
    response = client.get("/api/meal-plans")

    assert response.status_code == 200
    assert response.json() == []


def test_get_meal_plan_returns_404_for_unknown_id(client: TestClient) -> None:
    response = client.get("/api/meal-plans/999")

    assert response.status_code == 404
