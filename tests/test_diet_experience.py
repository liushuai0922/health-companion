from copy import deepcopy
from datetime import date, timedelta
from fastapi.testclient import TestClient
from backend.app.main import create_app
from core.clock import local_today
from core.nutrition.scoring import score_day


def intake():
    return {"patient": {"name": "林先生（演示）", "age": 42, "sex": "male", "height_cm": 172, "weight_kg": 82, "dietary_preferences": ["体重管理"]}, "conditions": ["hyperlipidemia", "fatty_liver"], "medications": []}


def diary():
    return {"day": "2026-06-01", "day_complete": True, "meals": [
        {"name": "breakfast", "status": "recorded", "items": [{"food_id": "oats", "servings": 1}]},
        {"name": "lunch", "status": "recorded", "items": [{"food_id": "vegetables", "servings": 2}, {"food_id": "fish", "servings": 1}]},
        {"name": "dinner", "status": "recorded", "items": [{"food_id": "vegetables", "servings": 1}, {"food_id": "tofu", "servings": 1}]},
        {"name": "snack", "status": "skipped", "items": []}
    ]}


def test_intake_demo_and_edit_do_not_duplicate(client):
    response = client.post("/intake", json=intake())
    assert response.status_code == 201
    profile = response.json()
    pid = profile["patient"]["id"]
    assert profile["patient"]["bmi"] == 27.72
    assert profile["medications"] == []
    guide = client.get(f"/patients/{pid}/diet-guide").json()
    assert {c["constraint"] for c in guide["nutrition"]["constraints"]} == {"saturated_fat", "fiber", "added_sugar", "alcohol"}
    changed = intake()
    changed["patient"]["weight_kg"] = 80
    assert client.put(f"/patients/{pid}/intake", json=changed).status_code == 200
    assert len(client.get("/patients").json()) == 1
    assert len(client.get(f"/patients/{pid}/conditions").json()) == 2


def test_bad_intake_atomic(client):
    bad = intake()
    bad["conditions"] = ["not_supported"]
    assert client.post("/intake", json=bad).status_code == 422
    assert client.get("/patients").json() == []


def test_score_deterministic_and_sensitive_to_choices():
    profile = intake()["patient"]
    conditions = [{"disease_code": c, "status": "active"} for c in intake()["conditions"]]
    good = score_day(profile, conditions, diary())
    assert good["score"] == 100
    poor_diary = diary()
    poor_diary["meals"][0]["items"] = [{"food_id": "sweet_drink", "servings": 2}, {"food_id": "cake", "servings": 1}]
    poor_diary["meals"][2]["items"] = [{"food_id": "beer", "servings": 1}, {"food_id": "fatty_meat", "servings": 2}]
    poorer = score_day(profile, conditions, poor_diary)
    assert poorer["score"] < good["score"]
    assert poorer == score_day(profile, list(reversed(conditions)), poor_diary)
    assert all(d["formula"] and d["evidence_source"] for d in poorer["dimensions"])


def test_partial_unknown_and_empty_do_not_get_score():
    profile = intake()["patient"]
    partial = diary() | {"day_complete": False}
    assert score_day(profile, [], partial)["score"] is None
    unknown = diary()
    unknown["meals"][0]["items"] = [{"food_id": "other", "servings": 1, "description": "混合盖浇饭"}]
    assert score_day(profile, [], unknown)["score"] is None
    empty = diary()
    for meal in empty["meals"]:
        meal.update(status="skipped", items=[])
    assert score_day(profile, [], empty)["score"] is None
    assert score_day(profile | {"age": 12}, [], diary())["score"] is None


def test_nutrition_estimate_and_incomplete_record_suppress_comparison():
    profile = intake()["patient"]
    logged = diary() | {"activity_level": "inactive"}
    estimate = score_day(profile, [], logged)["nutrition_estimate"]
    assert estimate["totals"]["energy_kcal"] == 142 + 23 * 3 + 105 + 78
    assert estimate["reference_kcal"] == 2028
    assert next(x for x in estimate["comparisons"] if x["key"] == "energy")["status"] == "可能偏少"
    assert estimate["comparisons"]
    partial = score_day(profile, [], logged | {"day_complete": False})["nutrition_estimate"]
    assert partial["totals"] == estimate["totals"]
    assert partial["comparisons"] == []
    unknown = diary() | {"activity_level": "inactive"}
    unknown["meals"][0]["items"].append({"food_id": "other", "servings": 1, "description": "混合菜饭"})
    missing = score_day(profile, [], unknown)["nutrition_estimate"]
    assert missing["omitted"] == ["混合菜饭"]
    assert missing["comparisons"] == []


def test_diary_persistence_and_upsert(client, database_url):
    pid = client.post("/intake", json=intake()).json()["patient"]["id"]
    url = f"/patients/{pid}/diet-days/2026-06-01"
    response = client.put(url, json=diary())
    assert response.status_code == 200
    assert response.json()["result"]["score"] == 100
    assert response.json()["profile_snapshot"]["patient"]["weight_kg"] == 82
    with TestClient(create_app(database_url)) as reopened:
        assert reopened.get(url).json() == response.json()
    partial = diary() | {"day_complete": False}
    assert client.put(url, json=partial).json()["result"]["score"] is None
    assert len(client.get(f"/patients/{pid}/diet-days").json()) == 1


def test_diary_validation(client):
    pid = client.post("/intake", json=intake()).json()["patient"]["id"]
    url = f"/patients/{pid}/diet-days/2026-06-01"
    for replacement in [{"food_id": "invented", "servings": 1}, {"food_id": "oats", "servings": -1}, {"food_id": "other", "servings": 1}]:
        invalid = diary()
        invalid["meals"][0]["items"] = [replacement]
        assert client.put(url, json=invalid).status_code == 422
    invalid = diary()
    invalid["meals"][0]["status"] = "skipped"
    assert client.put(url, json=invalid).status_code == 422
    assert client.get(url).status_code == 404
    future = (local_today() + timedelta(days=1)).isoformat()
    assert client.put(f"/patients/{pid}/diet-days/{future}", json=diary() | {"day": future}).status_code == 422


def test_medications_survive_edit_and_ownership_checked(client):
    data = intake()
    data["medications"] = [{"drug_name": "测试药", "generic_name": "demo", "dose": 1, "unit": "片", "administration_time": ["08:00"], "start_date": "2026-01-01"}]
    profile = client.post("/intake", json=data).json()
    pid = profile["patient"]["id"]
    med_id = profile["medications"][0]["id"]
    data["medications"][0]["id"] = med_id
    assert client.put(f"/patients/{pid}/intake", json=data).json()["medications"][0]["id"] == med_id
    other = client.post("/intake", json=intake()).json()["patient"]["id"]
    assert client.put(f"/patients/{other}/intake", json=data).status_code == 422
    data["medications"] = []
    assert client.put(f"/patients/{pid}/intake", json=data).json()["medications"] == []
    assert len(client.get(f"/patients/{pid}/medications?active_only=false").json()) == 1


def test_gout_guide_has_verified_source_and_intake_option(client):
    catalog = client.get("/catalog/diseases").json()
    assert catalog["gout"]["name"] == "痛风"
    assert catalog["hyperuricemia"]["evidence_source"].startswith("https://www.nhc.gov.cn/")
    detail = client.get("/catalog/gout-guide").json()
    assert set(detail["applies_to"]) == {"gout", "hyperuricemia"}
    assert "肾功能" in detail["scope"]
    assert len(detail["sections"]) >= 5
    payload = intake() | {"conditions": ["gout"]}
    pid = client.post("/intake", json=payload).json()["patient"]["id"]
    plan = client.get(f"/patients/{pid}/diet-guide").json()
    assert {c["constraint"] for c in plan["nutrition"]["constraints"]} == {"high_purine_food", "added_sugar", "alcohol", "hydration"}


def test_combined_guidance_for_multiple_diseases(client):
    payload = intake() | {"conditions":["fatty_liver","hyperlipidemia","gout","type2_diabetes"]}
    pid = client.post("/intake",json=payload).json()["patient"]["id"]
    guide = client.get(f"/patients/{pid}/diet-guide").json()
    combined = guide["combined_guidance"]
    shared = {x["topic"]:x for x in combined["common_goals"]}
    assert "added_sugar" in shared and len(shared["added_sugar"]["diseases"]) == 3
    assert "saturated_fat" in shared
    assert "high_purine_food" in {x["topic"] for x in combined["specific_goals"]}
    assert "hydration" in {x["topic"] for x in combined["review_goals"]}
    assert any("鱼和海鲜" in note for note in combined["combination_notes"])
    assert "鸡蛋、低脂奶" in combined["meal_approach"]
    assert len(guide["disease_guides"]) == 4
    assert all(d["source_url"].startswith("https://") and d["sections"] for d in guide["disease_guides"])

def test_duplicate_gout_conditions_get_one_detail_guide(client):
    payload = intake() | {"conditions":["gout","hyperuricemia"]}
    pid = client.post("/intake",json=payload).json()["patient"]["id"]
    guide = client.get(f"/patients/{pid}/diet-guide").json()
    assert [d["key"] for d in guide["disease_guides"]] == ["uric_acid"]
    assert guide["combined_guidance"]["common_goals"] == []
