from fastapi.testclient import TestClient
from backend.app.main import create_app
from scripts.seed_demo import seed_demo


def test_seed_idempotent_and_all_categories_reachable(database_url):
    app = create_app(database_url)
    with TestClient(app) as client:
        patient_id = seed_demo(app.state.sessions, interaction_demo=True)
        assert seed_demo(app.state.sessions, interaction_demo=True) == patient_id
        assert len(client.get("/patients").json()) == 1
        plan = client.get(f"/patients/{patient_id}/care-plan?foods=grapefruit&foods=high_sodium_food").json()
        assert len(plan["medication_plan"]) == 4
        assert {a["category"] for a in plan["safety"]["alerts"]} == {"drug_drug", "drug_disease", "drug_food", "disease_food", "duplicate_medication", "medication_meal_timing"}


def test_default_demo_is_fatty_liver_without_invented_prescription(database_url):
    app = create_app(database_url)
    with TestClient(app) as client:
        patient_id = seed_demo(app.state.sessions)
        assert seed_demo(app.state.sessions) == patient_id
        assert client.get("/demo-info").json()["patient_id"] == patient_id
        data = client.get(f"/patients/{patient_id}/intake").json()
        assert data["patient"]["age"] == 42
        assert data["patient"]["bmi"] == 27.72
        assert {c["disease_code"] for c in data["conditions"]} == {"fatty_liver", "hyperlipidemia"}
        assert data["medications"] == []


def test_local_browser_entry_and_docs(client):
    assert client.get("/").status_code == 200
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert 'src="/static/swagger-ui-bundle.js"' in docs.text
    assert 'href="/static/swagger-ui.css"' in docs.text
    assert "cdn.jsdelivr" not in docs.text
    assert client.get("/static/swagger-ui-bundle.js").status_code == 200
    assert client.get("/static/swagger-ui.css").status_code == 200
