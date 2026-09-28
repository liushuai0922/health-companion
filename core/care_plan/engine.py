from datetime import datetime
from core.clock import LOCAL_TIMEZONE
from core.disease.engine import evaluate_diseases
from core.interactions.engine import safety_check
from core.medication.engine import medication_plan
from core.nutrition.engine import nutrition_plan
from core.rules import load_rules


def observation_date(observation):
    stamp = datetime.fromisoformat(observation["measured_at"])
    return stamp.astimezone(LOCAL_TIMEZONE).date()


def generate_care_plan(patient, conditions, medications, observations, events, day, foods=None):
    defaults = load_rules("care_plan_defaults.json")
    disease = evaluate_diseases(conditions)
    nutrition = nutrition_plan(conditions, patient.get("dietary_preferences"), patient.get("allergies"))
    medication_items = medication_plan(medications, day, events)
    safety = safety_check(conditions, medications, day, foods)
    tasks = []
    for task in disease["monitoring"]:
        matching = sorted(o["id"] for o in observations if o["metric_type"] == task["type"] and observation_date(o) == day)
        tasks.append(task | {"status": "completed" if matching else "pending", "observation_ids": matching})
    timeline = [{"kind": "meal", "status": "suggested", **meal} for meal in defaults["meal_times"]]
    timeline += [{"kind": "monitoring", **task} for task in tasks]
    for med in medication_items:
        delayed = med["event"].get("delayed_to") if med["status"] == "delayed" else None
        timeline.append({"kind": "medication", "label": med["drug_name"], **med, "time": delayed or med["time"], "scheduled_time": med["time"]})
    timeline.sort(key=lambda item: (item["time"], item["kind"], item["label"], item.get("medication_id", 0)))
    return {
        "patient_id": patient["id"], "date": day.isoformat(), "timezone": defaults["timezone"], "demo": True,
        "medication_plan": medication_items, "nutrition": nutrition,
        "health_tasks": tasks, "safety": safety, "daily_timeline": timeline,
        "meal_timing_suggestions": [a for a in safety["alerts"] if a["category"] == "medication_meal_timing"],
        "schedule_note": defaults["schedule_note"],
        "observation_note": "健康指标用于展示和标记记录任务，不进行疾病诊断、指标风险分级或剂量计算。",
        "rules_versions": {"disease": disease["rule_version"], "interactions": safety["rule_version"], "schedule": defaults["version"]},
    }
