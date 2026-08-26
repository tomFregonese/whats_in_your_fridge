from fastapi.testclient import TestClient


def test_add_list_and_delete_allergy(client: TestClient) -> None:
    created = client.post(
        "/api/allergies", json={"ingredient_name": "peanut", "notes": "anaphylaxis"}
    )
    assert created.status_code == 201
    allergy_id = created.json()["id"]

    listed = client.get("/api/allergies").json()
    assert [a["ingredient_name"] for a in listed] == ["peanut"]

    deleted = client.delete(f"/api/allergies/{allergy_id}")
    assert deleted.status_code == 204
    assert client.get("/api/allergies").json() == []


def test_delete_unknown_allergy_returns_404(client: TestClient) -> None:
    response = client.delete("/api/allergies/999")

    assert response.status_code == 404
