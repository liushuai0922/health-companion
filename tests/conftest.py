import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app


@pytest.fixture
def database_url(tmp_path):
    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


@pytest.fixture
def client(database_url):
    with TestClient(create_app(database_url)) as client:
        yield client


@pytest.fixture
def patient(client):
    response = client.post("/patients", json={"name": "演示用户", "age": 35, "height_cm": 170, "weight_kg": 68})
    assert response.status_code == 201
    return response.json()
