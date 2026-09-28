from collections import defaultdict
from core.disease.engine import evaluate_diseases

SEVERITY = {"low": 0, "moderate": 1, "high": 2}
DIRECTION = {"increase": 0, "limit": 1, "avoid": 2, "review": 3}


def merge_constraints(constraints):
    grouped = defaultdict(list)
    for item in constraints:
        grouped[item["constraint"]].append(item)
    merged = []
    for key, items in sorted(grouped.items()):
        ordered = sorted(items, key=lambda x: (-x["priority"], -SEVERITY[x["severity"]], -DIRECTION[x["direction"]], x["id"], x["source"]))
        winner = ordered[0]
        directions = {item["direction"] for item in ordered}
        conflict = "increase" in directions and bool(directions & {"limit", "avoid"})
        effective = "review" if conflict or "review" in directions else winner["direction"]
        merged.append({
            "constraint": key, "direction": effective,
            "selected_rule_id": winner["id"], "priority": winner["priority"], "severity": winner["severity"],
            "sources": sorted({x["source"] for x in ordered}), "provenance": ordered,
            "needs_review": effective == "review", "conflict": conflict,
            "explanation": "存在方向相反的规则，请专业人员确认后再执行。" if conflict else winner["explanation"],
            "resolution": "priority > severity > restrictiveness > rule_id; opposing directions require review",
        })
    return merged


def nutrition_plan(conditions, preferences=None, allergies=None):
    disease = evaluate_diseases(conditions)
    constraints = merge_constraints(disease["constraints"])
    return {
        "demo": True, "rule_version": disease["rule_version"], "constraints": constraints,
        "recommended": [c for c in constraints if c["direction"] == "increase"],
        "limit": [c for c in constraints if c["direction"] == "limit"],
        "avoid": [c for c in constraints if c["direction"] == "avoid"],
        "review": [c for c in constraints if c["direction"] == "review"],
        "dietary_preferences": preferences or [], "allergies": allergies or [],
        "personalization_note": "偏好和过敏信息已保留；当前不生成食谱、不判定食物过敏安全性，偏好不会覆盖疾病约束。",
        "unsupported_conditions": disease["unsupported_conditions"],
    }
