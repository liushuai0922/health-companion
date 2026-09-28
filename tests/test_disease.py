from core.disease.engine import evaluate_diseases


def test_disease_rules_traceable_and_inactive_ignored():
    result = evaluate_diseases([{"disease_code": "hypertension", "status": "active"}, {"disease_code": "type2_diabetes", "status": "resolved"}])
    assert [x["constraint"] for x in result["constraints"]] == ["sodium"]
    assert result["constraints"][0]["source"] == "hypertension"
    assert result["constraints"][0]["evidence_source"].startswith("https://")
    assert len(result["monitoring"]) == 1


def test_unknown_disease_is_explicit():
    result = evaluate_diseases([{"disease_code": "CKD", "status": "active"}])
    assert result["unsupported_conditions"] == ["CKD"]


def test_conditions_api(client, patient):
    url = f"/patients/{patient['id']}/conditions"
    payload = {"disease_code": "hypertension"}
    assert client.post(url, json=payload).status_code == 201
    assert client.post(url, json=payload).status_code == 409
    assert len(client.get(url).json()) == 1
    assert client.post(url, json={"disease_code": "unknown"}).status_code == 422
    assert client.get("/patients/999/conditions").status_code == 404
