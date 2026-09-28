from fastapi.testclient import TestClient
from backend.app.main import create_app


def test_patient_persists_after_app_restart(client, patient, database_url):
    assert patient["bmi"] == 23.53
    with TestClient(create_app(database_url)) as reopened:
        response = reopened.get(f"/patients/{patient['id']}")
        assert response.status_code == 200
        assert response.json() == patient


def test_unknown_patient(client):
    assert client.get("/patients/999").status_code == 404


def test_invalid_patient(client):
    for change in [{"age": -1}, {"height_cm": 0}, {"weight_kg": -10}, {"name": " "}, {"sex": "invalid"}]:
        payload = {"name": "Test", "age": 28, "height_cm": 170, "weight_kg": 60} | change
        assert client.post("/patients", json=payload).status_code == 422
