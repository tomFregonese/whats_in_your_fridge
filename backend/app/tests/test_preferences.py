from fastapi.testclient import TestClient


def test_add_list_and_delete_preference(client: TestClient) -> None:
    created = client.post("/api/preferences", json={"content": "loves spicy food"})
    assert created.status_code == 201
    assert created.json()["source"] == "manual"
    preference_id = created.json()["id"]

    listed = client.get("/api/preferences").json()
    assert [p["content"] for p in listed] == ["loves spicy food"]

    deleted = client.delete(f"/api/preferences/{preference_id}")
    assert deleted.status_code == 204
    assert client.get("/api/preferences").json() == []


def test_delete_unknown_preference_returns_404(client: TestClient) -> None:
    response = client.delete("/api/preferences/999")

    assert response.status_code == 404
