from datetime import date
from core.care_plan.engine import generate_care_plan


def test_core_care_plan_deterministic():
    patient = {"id": 1, "dietary_preferences": ["清淡"], "allergies": ["花生"]}
    conditions = [{"disease_code": "hypertension", "status": "active"}]
    med = {"id": 1, "drug_name": "Demo", "generic_name": "demo", "dose": 1, "unit": "片", "route": "oral", "active": True, "start_date": "2026-01-01", "end_date": None, "administration_time": ["08:30"], "meal_relation": "after_meal"}
    event = {"medication_id": 1, "scheduled_date": "2026-06-01", "scheduled_time": "08:30", "status": "delayed", "delayed_to": "09:30"}
    args = (patient, conditions, [med], [], [event], date(2026, 6, 1))
    result = generate_care_plan(*args)
    assert result == generate_care_plan(*args)
    assert result["nutrition"]["allergies"] == ["花生"]
    assert result["health_tasks"][0]["status"] == "pending"
    timeline = result["daily_timeline"]
    assert [i["time"] for i in timeline] == sorted(i["time"] for i in timeline)
    dose = next(i for i in timeline if i["kind"] == "medication")
    assert dose["time"] == "09:30" and dose["scheduled_time"] == "08:30"


def test_observations_validation_and_timezone(client, patient):
    prefix = f"/patients/{patient['id']}"
    client.post(prefix + "/conditions", json={"disease_code": "hypertension"})
    payload = {"metric_type": "blood_pressure", "systolic": 125, "diastolic": 80, "unit": "mmHg", "measured_at": "2026-06-01T07:30:00+08:00"}
    response = client.post(prefix + "/observations", json=payload)
    assert response.status_code == 201
    assert response.json()["measured_at"] == "2026-05-31T23:30:00Z"
    for change in [{"unit": "mg"}, {"systolic": 70}, {"value": 120}, {"measured_at": "2026-06-01T07:30:00"}]:
        assert client.post(prefix + "/observations", json=payload | change).status_code == 422
    assert len(client.get(prefix + "/observations").json()) == 1
    today = client.get(prefix + "/care-plan?day=2026-06-01").json()
    yesterday = client.get(prefix + "/care-plan?day=2026-05-31").json()
    assert today["health_tasks"][0]["status"] == "completed"
    assert yesterday["health_tasks"][0]["status"] == "pending"


def test_api_care_plan(client, patient):
    prefix = f"/patients/{patient['id']}"
    for code in ["hypertension", "type2_diabetes", "hyperlipidemia"]:
        assert client.post(prefix + "/conditions", json={"disease_code": code}).status_code == 201
    response = client.get(prefix + "/care-plan?day=2026-06-01")
    assert response.status_code == 200
    result = response.json()
    assert len(result["nutrition"]["constraints"]) == 5
    assert len(result["health_tasks"]) == 2
    assert result["medication_plan"] == []
    assert result["safety"]["demo"] is True
    assert result == client.get(prefix + "/care-plan?day=2026-06-01").json()
    assert client.get("/patients/999/care-plan").status_code == 404


def test_all_observation_types(client, patient):
    catalog = client.get("/catalog/observation-types").json()
    assert len(catalog) == 13
    for metric, unit in catalog.items():
        values = {"systolic": 120, "diastolic": 80} if metric == "blood_pressure" else {"value": 5}
        response = client.post(f"/patients/{patient['id']}/observations", json={"metric_type": metric, "unit": unit, "measured_at": "2026-06-01T07:00:00+08:00", **values})
        assert response.status_code == 201
