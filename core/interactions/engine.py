import json
from collections import defaultdict
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from core.medication.engine import is_scheduled
from core.rules import RULES_DIR, load_rules

Category = Literal["drug_drug", "drug_disease", "drug_food", "disease_food", "duplicate_medication", "medication_meal_timing"]
SEVERITY = {"high": 0, "moderate": 1, "low": 2}


class Trigger(BaseModel):
    model_config = ConfigDict(extra="forbid")
    drugs_all: list[str] = Field(default_factory=list)
    conditions_any: list[str] = Field(default_factory=list)
    foods_any: list[str] = Field(default_factory=list)
    routes: list[str] = Field(default_factory=list)
    duplicate_generic: bool = False
    meal_relations_any: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def nonempty(self):
        if not (self.drugs_all or self.conditions_any or self.foods_any or self.duplicate_generic or self.meal_relations_any):
            raise ValueError("A rule must have a supported trigger")
        return self


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    category: Category
    trigger: Trigger
    severity: Literal["low", "moderate", "high"]
    explanation: str
    action: str
    evidence_source: str


def read_catalog(kind):
    return json.loads((RULES_DIR.parent / kind / "catalog.json").read_text(encoding="utf-8-sig"))[kind]


def normalize(name, catalog):
    name = name.strip().casefold()
    for code, details in catalog.items():
        if name in {code, *(alias.casefold() for alias in details["aliases"])}:
            return code
    return name


def safety_check(conditions, medications, day, foods=None):
    bundle = load_rules("interaction_rules.json")
    rules = [Rule.model_validate(r) for r in bundle["rules"]]
    if len({r.id for r in rules}) != len(rules):
        raise ValueError("Duplicate interaction rule IDs")
    drug_catalog, food_catalog = read_catalog("drugs"), read_catalog("foods")
    active = [m | {"canonical_name": normalize(m["generic_name"], drug_catalog)} for m in medications if is_scheduled(m, day)]
    disease_codes = {c["disease_code"] for c in conditions if c["status"] == "active"}
    food_codes = {normalize(f, food_catalog) for f in (foods or [])}
    alerts = []
    for rule in rules:
        trigger = rule.trigger
        eligible = [m for m in active if not trigger.routes or m["route"] in trigger.routes]
        if trigger.drugs_all and not set(trigger.drugs_all) <= {m["canonical_name"] for m in eligible}:
            continue
        if trigger.conditions_any and not disease_codes.intersection(trigger.conditions_any):
            continue
        if trigger.foods_any and foods is not None and not food_codes.intersection(trigger.foods_any):
            continue
        matched = [m for m in eligible if m["canonical_name"] in trigger.drugs_all] if trigger.drugs_all else []
        groups = [matched]
        if trigger.duplicate_generic:
            duplicates = defaultdict(list)
            for med in eligible:
                duplicates[med["canonical_name"]].append(med)
            groups = [v for _, v in sorted(duplicates.items()) if len(v) > 1]
        elif trigger.meal_relations_any:
            groups = [[m] for m in eligible if m["meal_relation"] in trigger.meal_relations_any]
        for group in groups:
            conditional = bool(trigger.foods_any and foods is None)
            alerts.append({
                "rule_id": rule.id, "version": bundle["version"], "demo": bundle["demo"],
                "category": rule.category, "severity": rule.severity,
                "explanation": rule.explanation, "action": rule.action, "evidence_source": rule.evidence_source,
                "trigger": trigger.model_dump(exclude_defaults=True),
                "exposure_status": "potential_not_recorded" if conditional else "recorded",
                "exposure_note": "饮食未提供；这是条件性提醒，不代表已经食用。" if conditional else "依据当前输入记录匹配。",
                "matched_data": {
                    "date": day.isoformat(),
                    "medications": [{k: m[k] for k in ["id", "drug_name", "generic_name", "canonical_name", "route", "meal_relation"]} for m in sorted(group, key=lambda m: m["id"])],
                    "conditions": sorted(disease_codes.intersection(trigger.conditions_any)),
                    "foods": sorted(food_codes.intersection(trigger.foods_any)),
                },
            })
    alerts.sort(key=lambda a: (SEVERITY[a["severity"]], a["rule_id"], [m["id"] for m in a["matched_data"]["medications"]]))
    return {
        "date": day.isoformat(), "demo": True, "rule_version": bundle["version"], "alerts": alerts,
        "coverage": {
            "message": "仅为少量演示规则。未命中不表示安全；未评估剂量、肾功能、肝功能、妊娠、过敏和所有相互作用。",
            "categories": sorted({r.category for r in rules}),
            "unknown_drugs": sorted({m["generic_name"] for m in active if m["canonical_name"] not in drug_catalog}),
            "unknown_foods": sorted(food_codes - set(food_catalog)),
            "food_input_provided": foods is not None,
        },
    }
