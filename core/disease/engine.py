from core.rules import load_rules


def catalog():
    return load_rules("disease_rules.json")["diseases"]


def evaluate_diseases(conditions):
    rules = load_rules("disease_rules.json")
    constraints, monitoring, unsupported = [], [], []
    for code in sorted({c["disease_code"] for c in conditions if c["status"] == "active"}):
        rule = rules["diseases"].get(code)
        if rule is None:
            unsupported.append(code)
            continue
        for item in rule["constraints"]:
            constraints.append(item | {"source": code, "evidence_source": rule["evidence_source"], "version": rules["version"], "demo": rules["demo"]})
        for item in rule["monitoring"]:
            monitoring.append(item | {"source": code, "demo": True, "schedule_note": "演示时间，监测频率和时间须按已确认计划调整。"})
    return {"constraints": constraints, "monitoring": monitoring, "unsupported_conditions": unsupported, "rule_version": rules["version"]}
