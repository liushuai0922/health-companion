import json
from core.rules import RULES_DIR, load_rules
from core.activity.engine import exercise_catalog


def diet_catalog():
    return json.loads((RULES_DIR.parent / "foods" / "diet_catalog.json").read_text(encoding="utf-8-sig"))


def nutrition_catalog():
    return json.loads((RULES_DIR.parent / "foods" / "nutrition_estimates.json").read_text(encoding="utf-8-sig"))


def estimate_nutrition(profile, conditions, diary, food_names):
    catalog = nutrition_catalog()
    values = catalog["foods"]
    fields = ("energy_kcal", "protein_g", "fat_g", "carbohydrate_g", "fiber_g", "sodium_mg")
    totals = {field: 0.0 for field in fields}
    covered = {field: True for field in fields}
    omitted, details = [], []
    for meal in diary["meals"]:
        for item in meal["items"]:
            food_id = item["food_id"]
            data = values.get(food_id)
            name = item.get("description") if food_id == "other" else food_names[food_id]
            if data is None:
                omitted.append(name or food_id)
                for field in fields:
                    covered[field] = False
                continue
            factor = data["portion_g"] * item["servings"] / 100
            item_energy = data["per_100g"]["energy_kcal"]
            details.append({"meal": meal["name"], "name": name, "servings": item["servings"], "grams": round(data["portion_g"] * item["servings"]), "energy_kcal": round(item_energy * factor) if item_energy is not None else None, "fdc_id": data["fdc_id"], "source_url": data["source_url"], "assumption": data["note"]})
            for field in fields:
                value = data["per_100g"][field]
                if value is None:
                    covered[field] = False
                else:
                    totals[field] += value * factor
    totals = {field: round(value) if field in ("energy_kcal", "sodium_mg") else round(value, 1) for field, value in totals.items()}
    day_complete = diary["day_complete"] and all(meal["status"] != "unreported" for meal in diary["meals"])
    comparison_ready = day_complete and bool(details) and not omitted and covered["energy_kcal"]
    activity = diary.get("activity_level")
    factors = {"inactive": 1.2, "light_active": 1.3, "low_active": 1.375, "active": 1.55, "very_active": 1.725}
    reference = None
    if profile["age"] >= 18 and profile.get("sex") in ("male", "female") and activity in factors:
        resting = 10 * profile["weight_kg"] + 6.25 * profile["height_cm"] - 5 * profile["age"] + (5 if profile["sex"] == "male" else -161)
        reference = round(resting * factors[activity])
    comparisons = []
    if comparison_ready and reference is not None:
        ratio = totals["energy_kcal"] / reference
        comparisons.append({"key": "energy", "label": "总热量", "actual": totals["energy_kcal"], "reference": reference, "unit": "kcal", "status": "可能偏少" if ratio < .8 else "可能偏多" if ratio > 1.2 else "接近估算维持需求"})
        special_protein = any(c["status"] == "active" and c["disease_code"] in ("chronic_kidney_disease", "ckd") for c in conditions) or profile["age"] >= 65
        if covered["protein_g"] and not special_protein:
            protein_ref = round(profile["weight_kg"] * .8, 1)
            comparisons.append({"key": "protein", "label": "蛋白质", "actual": totals["protein_g"], "reference": protein_ref, "unit": "g", "status": "低于一般成人参考" if totals["protein_g"] < protein_ref * .8 else "达到或高于一般成人参考"})
        if covered["fiber_g"]:
            fiber_ref = round(reference / 1000 * 14, 1)
            comparisons.append({"key": "fiber", "label": "膳食纤维", "actual": totals["fiber_g"], "reference": fiber_ref, "unit": "g", "status": "可能偏少" if totals["fiber_g"] < fiber_ref * .8 else "达到或高于一般参考"})
    notes = ["按食物目录的默认克数和 USDA 代表食品估算；烹调油、盐、糖、酱汁及品牌差异常未计入，数值可能明显偏离实际。", "热量参考是维持当前体重的粗略估计，不是减重目标；单日结果不能判断营养是否充足。"]
    if not day_complete:
        notes.append("当天记录未确认完整，数值仅为已记食物小计，不作多少判断。")
    if omitted:
        notes.append("未计入：" + "、".join(omitted) + "；小计不能代表全天总量。")
    if reference is None:
        notes.append("未提供可计算的成人性别与活动水平，或年龄未满 18 岁；不作热量需求比较。")
    if profile["age"] >= 65 or any(c["status"] == "active" and c["disease_code"] in ("chronic_kidney_disease", "ckd") for c in conditions):
        notes.append("老年人或肾病人群的蛋白质需要应按个人情况评估，此处不作一般成人蛋白质比较。")
    exercise_id = diary.get("exercise_activity_id")
    exercise = next((item for item in exercise_catalog()["activities"] if item["id"] == exercise_id), None) if exercise_id else None
    if exercise:
        notes.append("单次运动不单独从摄入热量中扣除；维持热量参考仅按所选整体活动水平粗估。")
    return {"version": catalog["version"], "totals": totals, "covered": covered, "items": details, "omitted": omitted, "complete": day_complete, "reference_kcal": reference, "activity_level": activity, "activity_factor": factors.get(activity), "recorded_exercise": {"id": exercise_id, "name": exercise["name"], "minutes": diary.get("exercise_minutes", 0)} if exercise else None, "comparisons": comparisons, "notes": notes, "sources": {"food": catalog["source_url"], "resting_energy": "https://pubmed.ncbi.nlm.nih.gov/2305711/", "protein": "https://ods.od.nih.gov/HealthInformation/nutrientrecommendations/", "fiber": "https://www.dietaryguidelines.gov/sites/default/files/2020-12/Dietary_Guidelines_for_Americans_2020-2025.pdf"}}


def score_day(profile, conditions, diary):
    rules = load_rules("diet_score_rules.json")
    foods = {food["id"]: food for food in diet_catalog()["foods"]}
    codes = {c["disease_code"] for c in conditions if c["status"] == "active"}
    totals = {}
    unknown, allergy_notes, items = [], [], []
    for meal in diary["meals"]:
        for entry in meal["items"]:
            food = foods[entry["food_id"]]
            items.append(entry)
            if entry["food_id"] == "other":
                unknown.append(entry["description"])
            for tag, value in food["tags"].items():
                totals[tag] = totals.get(tag, 0) + value * entry["servings"]
            matches = sorted(set(profile.get("allergies", [])) & set(food["allergens"]))
            if matches:
                allergy_notes.append(f"{food['name']} 与记录的过敏信息（{'、'.join(matches)}）存在字典匹配，请核对。")
    blockers = []
    if not diary["day_complete"] or any(m["status"] == "unreported" for m in diary["meals"]):
        blockers.append("请补全各餐状态，并确认今天所有饮食都已记录。")
    if not items:
        blockers.append("还没有食物记录；没有吃东西不会获得高分。")
    if unknown:
        blockers.append("有未识别食物，本次先保存记录，不计算总分。")
    if profile["age"] < 18:
        blockers.append("当前演示评分仅面向成年人，未成年人需要适龄饮食指导。")
    dimensions = []
    for rule in rules["dimensions"]:
        amount = totals.get(rule["id"], 0)
        weight = max([rule["weight"], *[w for c, w in rule["condition_weights"].items() if c in codes]])
        if rule["mode"] == "increase":
            ratio = min(amount / rule["target"], 1)
        else:
            ratio = max(0, 1 - amount / 2)
        if rule["id"] == "alcohol":
            ratio = 1 if amount == 0 else 0
        dimensions.append({"id": rule["id"], "label": rule["label"], "amount": round(amount, 2), "weight": weight, "earned": round(weight * ratio, 2), "completion": round(ratio * 100), "hint": rule["hint"], "evidence_source": rule["source"], "weighted_for": sorted(c for c, w in rule["condition_weights"].items() if c in codes and w == weight), "formula": f"min(记录分类份数 / {rule['target']}, 1) × 权重" if rule["mode"] == "increase" else ("未记录酒精得该项分，否则为 0" if rule["id"] == "alcohol" else "max(0, 1 - 记录分类份数 / 2) × 权重")})
    total_weight = sum(d["weight"] for d in dimensions)
    score = None if blockers else round(sum(d["earned"] for d in dimensions) / total_weight * 100)
    suggestions = [d["hint"] for d in sorted(dimensions, key=lambda d: (-(d["weight"] - d["earned"]), d["id"])) if d["earned"] < d["weight"]][:3]
    return {"score": score, "label": "待补充记录" if score is None else ("更多习惯符合演示目标" if score >= 80 else "还有可以调整的地方" if score >= 60 else "先从一两个习惯开始"), "dimensions": dimensions, "total_weight": total_weight, "suggestions": suggestions, "blockers": blockers, "unknown_foods": unknown, "allergy_notes": sorted(set(allergy_notes)), "allergy_note": "仅对少量食物做名称匹配；未命中不代表无过敏风险。", "rule_version": rules["version"], "food_catalog_version": diet_catalog()["version"], "method": rules["method"], "limitations": rules["limitations"], "total_formula": "各项得分之和 / 各项权重之和 × 100，四舍五入", "demo": True, "condition_codes": sorted(codes), "nutrition_estimate": estimate_nutrition(profile, conditions, diary, {f["id"]: f["name"] for f in foods.values()})}
