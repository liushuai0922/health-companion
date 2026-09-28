from datetime import date
from core.interactions.engine import safety_check

DAY = date(2026, 6, 1)


def medication(id, name, **extra):
    return {"id": id, "generic_name": name, "drug_name": name, "active": True, "start_date": "2026-01-01", "end_date": None, "route": "oral", "meal_relation": "anytime"} | extra


def ids(result):
    return {a["rule_id"] for a in result["alerts"]}


def test_duplicate_alias_and_inactive_excluded():
    meds = [medication(1, "ATORVASTATIN"), medication(2, "阿托伐他汀钙片"), medication(3, "阿托伐他汀", active=False)]
    result = safety_check([], meds, DAY, [])
    assert ids(result) == {"DUPLICATE-GENERIC"}
    assert [m["id"] for m in result["alerts"][0]["matched_data"]["medications"]] == [1, 2]
    assert safety_check([], list(reversed(meds)), DAY, []) == result


def test_drug_food_has_provenance_and_exposure():
    meds = [medication(1, "atorvastatin")]
    recorded = safety_check([], meds, DAY, ["西柚汁"])
    assert ids(recorded) == {"DFOOD-ATORVASTATIN-GRAPEFRUIT"}
    assert recorded["alerts"][0]["matched_data"]["foods"] == ["grapefruit"]
    assert recorded["alerts"][0]["evidence_source"].startswith("https://www.fda.gov")
    potential = safety_check([], meds, DAY)
    assert potential["alerts"][0]["exposure_status"] == "potential_not_recorded"
    assert safety_check([], meds, DAY, ["apple"])["alerts"] == []


def test_drug_disease_and_drug_drug():
    conditions = [{"disease_code": "hypertension", "status": "active"}]
    meds = [medication(1, "ibuprofen"), medication(2, "warfarin")]
    result = safety_check(conditions, meds, DAY, [])
    assert ids(result) == {"DDIS-IBUPROFEN-HTN", "DDI-WARFARIN-IBUPROFEN"}
    assert result["alerts"][0]["severity"] == "high"
    assert safety_check(conditions, [medication(1, "ibuprofen", route="topical")], DAY, [])["alerts"] == []


def test_disease_food_meal_timing_and_unknown_coverage():
    conditions = [{"disease_code": "hypertension", "status": "active"}]
    result = safety_check(conditions, [medication(1, "unknown_drug", meal_relation="after_meal")], DAY, ["咸菜"])
    assert ids(result) == {"DISFOOD-HTN-SODIUM", "MED-MEAL-RECORDED"}
    assert result["coverage"]["unknown_drugs"] == ["unknown_drug"]


def test_expired_and_future_drugs_do_not_trigger():
    meds = [medication(1, "warfarin", end_date="2026-05-31"), medication(2, "ibuprofen", start_date="2026-06-02")]
    assert safety_check([], meds, DAY, [])["alerts"] == []


def test_api_safety_check(client, patient):
    prefix = f"/patients/{patient['id']}"
    client.post(prefix + "/conditions", json={"disease_code": "hypertension"})
    response = client.post(prefix + "/medications", json={"drug_name": "布洛芬", "generic_name": "ibuprofen", "dose": 200, "unit": "mg", "administration_time": ["08:30"], "start_date": "2026-01-01"})
    assert response.status_code == 201
    result = client.get(prefix + "/safety-check?day=2026-06-01&foods=high_sodium_food")
    assert result.status_code == 200
    assert "DDIS-IBUPROFEN-HTN" in ids(result.json())
    assert result.json() == client.get(prefix + "/safety-check?day=2026-06-01&foods=high_sodium_food").json()
