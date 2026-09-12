from fastapi.testclient import TestClient


def test_add_list_and_delete_equipment(client: TestClient) -> None:
    created = client.post("/api/equipment", json={"name": "oven"})
    assert created.status_code == 201
    equipment_id = created.json()["id"]

    listed = client.get("/api/equipment").json()
    assert [e["name"] for e in listed] == ["oven"]

    deleted = client.delete(f"/api/equipment/{equipment_id}")
    assert deleted.status_code == 204
    assert client.get("/api/equipment").json() == []


def test_delete_unknown_equipment_returns_404(client: TestClient) -> None:
    response = client.delete("/api/equipment/999")

    assert response.status_code == 404
