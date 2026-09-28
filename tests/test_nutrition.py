import pytest
from core.nutrition.engine import merge_constraints, nutrition_plan


@pytest.mark.parametrize("codes, expected", [
    (["hypertension"], {"sodium"}),
    (["hypertension", "type2_diabetes"], {"sodium", "added_sugar", "refined_carbohydrate", "fiber"}),
    (["hypertension", "type2_diabetes", "hyperlipidemia"], {"sodium", "added_sugar", "refined_carbohydrate", "fiber", "saturated_fat"}),
])
def test_single_two_three_diseases(codes, expected):
    conditions = [{"disease_code": c, "status": "active"} for c in codes]
    result = nutrition_plan(conditions)
    assert {x["constraint"] for x in result["constraints"]} == expected
    assert nutrition_plan(list(reversed(conditions))) == result
    if len(codes) == 3:
        fiber = next(c for c in result["constraints"] if c["constraint"] == "fiber")
        assert fiber["sources"] == ["hyperlipidemia", "type2_diabetes"]
        assert len(fiber["provenance"]) == 2


def test_conflict_is_not_silently_overridden():
    a = {"id": "a", "constraint": "fluid", "direction": "increase", "priority": 20, "severity": "low", "source": "a", "explanation": "demo"}
    b = a | {"id": "b", "direction": "limit", "priority": 90, "source": "b"}
    result = merge_constraints([a, b])[0]
    assert result["direction"] == "review"
    assert result["selected_rule_id"] == "b"
    assert result["conflict"] and result["needs_review"]
    assert merge_constraints([b, a])[0] == result


def test_nutrition_api(client, patient):
    prefix = f"/patients/{patient['id']}"
    client.post(prefix + "/conditions", json={"disease_code": "hypertension"})
    response = client.get(prefix + "/nutrition-constraints")
    assert response.status_code == 200
    assert response.json()["limit"][0]["constraint"] == "sodium"
