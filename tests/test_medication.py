import pytest


@pytest.fixture
def med_payload():
    return {"drug_name": "演示药 A", "generic_name": "demo_a", "dose": 1, "unit": "片", "administration_time": ["08:30"], "meal_relation": "after_meal", "start_date": "2026-01-01", "end_date": "2026-12-31"}


def test_medication_lifecycle_and_history(client, patient, med_payload):
    prefix = f"/patients/{patient['id']}"
    response = client.post(prefix + "/medications", json=med_payload)
    assert response.status_code == 201
    med_id = response.json()["id"]
    path = prefix + f"/medications/{med_id}"
    plan = prefix + "/medication-plan?day=2026-06-01"
    assert client.get(plan).json()["items"][0]["status"] == "pending"
    event = {"scheduled_date": "2026-06-01", "scheduled_time": "08:30", "status": "delayed", "delayed_to": "09:00"}
    assert client.put(path + "/events", json=event).status_code == 200
    event.update(status="taken", delayed_to=None, taken_at="2026-06-01T09:00:00+08:00")
    assert client.put(path + "/events", json=event).status_code == 200
    assert client.get(plan).json()["items"][0]["status"] == "taken"
    assert len(client.get(prefix + "/medication-history").json()) == 1
    assert client.put(path, json=med_payload | {"dose": 2}).status_code == 200
    assert client.get(prefix + "/medication-history").json()[0]["medication_snapshot"]["dose"] == 1
    assert client.post(path + "/deactivate").status_code == 200
    assert client.get(plan).json()["items"] == []
    assert len(client.get(prefix + "/medication-history").json()) == 1


def test_schedule_validation_and_boundaries(client, patient, med_payload):
    prefix = f"/patients/{patient['id']}"
    for changes in [{"dose": 0}, {"administration_time": ["25:00"]}, {"frequency": "twice_daily"}, {"end_date": "2025-01-01"}, {"administration_time": ["08:30", "08:30"]}]:
        assert client.post(prefix + "/medications", json=med_payload | changes).status_code == 422
    med = client.post(prefix + "/medications", json=med_payload).json()
    assert client.get(prefix + "/medication-plan?day=2025-12-31").json()["items"] == []
    assert client.get(prefix + "/medication-plan?day=2027-01-01").json()["items"] == []
    assert len(client.get(prefix + "/medication-plan?day=2026-12-31").json()["items"]) == 1
    event = {"scheduled_date": "2026-06-01", "scheduled_time": "07:00", "status": "missed"}
    assert client.put(prefix + f"/medications/{med['id']}/events", json=event).status_code == 422
    other = client.post("/patients", json={"name": "Other", "age": 20, "height_cm": 160, "weight_kg": 60}).json()
    assert client.post(f"/patients/{other['id']}/medications/{med['id']}/deactivate").status_code == 404


def test_missed_and_invalid_event(client, patient, med_payload):
    prefix = f"/patients/{patient['id']}"
    med = client.post(prefix + "/medications", json=med_payload).json()
    path = prefix + f"/medications/{med['id']}/events"
    event = {"scheduled_date": "2026-06-01", "scheduled_time": "08:30", "status": "missed"}
    assert client.put(path, json=event).status_code == 200
    assert client.get(prefix + "/medication-plan?day=2026-06-01").json()["items"][0]["status"] == "missed"
    assert client.put(path, json=event | {"status": "taken"}).status_code == 422
    assert client.put(path, json=event | {"status": "delayed", "delayed_to": "08:00"}).status_code == 422
