from datetime import date


def is_scheduled(medication, day):
    start = date.fromisoformat(str(medication["start_date"]))
    end = date.fromisoformat(str(medication["end_date"])) if medication.get("end_date") else None
    return medication["active"] and start <= day and (end is None or day <= end)


def medication_plan(medications, day, events=()):
    by_slot = {(e["medication_id"], e["scheduled_time"]): e for e in events if str(e["scheduled_date"]) == day.isoformat()}
    slots = []
    for med in medications:
        if not is_scheduled(med, day):
            continue
        for time in med["administration_time"]:
            event = by_slot.get((med["id"], time))
            slots.append({"medication_id": med["id"], "drug_name": med["drug_name"], "dose": med["dose"], "unit": med["unit"], "route": med["route"], "meal_relation": med["meal_relation"], "date": day.isoformat(), "time": time, "status": event["status"] if event else "pending", "event": event})
    return sorted(slots, key=lambda x: (x["time"], x["medication_id"]))
