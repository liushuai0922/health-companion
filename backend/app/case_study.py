from datetime import date, timedelta
from math import sin

from core.nutrition.scoring import diet_catalog, score_day


START = date(2026, 1, 1)
END = date(2026, 6, 30)
PROFILE = {"age": 42, "sex": "male", "height_cm": 172, "weight_kg": 82, "allergies": []}
CONDITIONS = [{"disease_code": code, "status": "active"} for code in ("fatty_liver", "hyperlipidemia")]
NAMES = {food["id"]: food["name"] for food in diet_catalog()["foods"]}


def case_day(index):
    day = START + timedelta(days=index)
    phase = day.month - 1
    # Templates improve in small steps, with occasional imperfect days.
    breakfasts = [
        ["whole_wheat", "milk", "cake"],
        ["whole_wheat", "egg", "milk"],
        ["oats", "egg", "milk"],
        ["oats", "egg", "milk"],
        ["oats", "egg", "milk"],
        ["oats", "egg", "milk"],
    ]
    lunches = [
        ["white_rice", "fried_chicken", "vegetables"],
        ["white_rice", "chicken", "vegetables"],
        ["brown_rice", "chicken", "vegetables"],
        ["brown_rice", "fish", "vegetables", "vegetables"],
        ["brown_rice", "fish", "vegetables", "vegetables"],
        ["brown_rice", "fish", "vegetables", "vegetables"],
    ]
    dinners = [
        ["white_rice", "fatty_meat", "pickles"],
        ["white_rice", "fatty_meat", "vegetables"],
        ["white_rice", "tofu", "vegetables"],
        ["white_rice", "tofu", "vegetables", "vegetables"],
        ["white_rice", "tofu", "vegetables", "vegetables"],
        ["white_rice", "tofu", "vegetables", "vegetables"],
    ]
    snacks = [["sweet_drink"], ["sweet_drink"], ["water", "apple"], ["water", "apple"], ["water", "apple", "nuts"], ["water", "apple", "nuts"]]
    food_ids = [list(breakfasts[phase]), list(lunches[phase]), list(dinners[phase]), list(snacks[phase])]
    if phase >= 2:
        food_ids[0].append("whole_wheat")
        if "nuts" not in food_ids[3]:
            food_ids[3].append("nuts")
    if index % 13 == 4:
        food_ids[3] = ["cake", "water"]  # a realistic off-plan day
    if index % 17 == 8 and phase >= 2:
        food_ids[1] = ["white_rice", "fried_chicken", "vegetables"]
    def servings(fid):
        if phase < 2:
            return 1
        return {"oats": 1.5, "brown_rice": 1.5, "white_rice": 1.5, "fish": 1.5, "tofu": 2}.get(fid, 1)

    diary = {"day": day.isoformat(), "day_complete": True, "meals": [{"name": name, "status": "recorded", "items": [{"food_id": fid, "servings": servings(fid), "description": ""} for fid in foods]} for name, foods in zip(("breakfast", "lunch", "dinner", "snack"), food_ids)]}
    result = score_day(PROFILE, CONDITIONS, diary)
    training_days = (0, 2, 4) if phase < 2 else (0, 1, 3, 5) if phase < 4 else (0, 1, 2, 4, 5)
    active = day.weekday() in training_days
    minutes = 0 if not active else [5, 8, 12, 18, 24, 30][phase] + (index % 3 - 1) * 2
    if minutes < 0:
        minutes = 0
    activity_id = "indoor_walk" if phase < 2 else "slow_walk"
    weight = round(82 - 6 * index / (END - START).days + 0.25 * sin(index / 5), 1)
    meal_text = ["、".join(NAMES[x] + (f"×{servings(x):g}份" if servings(x) != 1 else "") for x in foods) for foods in food_ids]
    return {"day": day.isoformat(), "day_number": index + 1, "phase": phase + 1, "breakfast": meal_text[0], "lunch": meal_text[1], "dinner": meal_text[2], "snacks": meal_text[3], "food_ids": food_ids, "diet_score": result["score"], "energy_kcal": result["nutrition_estimate"]["totals"]["energy_kcal"], "activity_id": activity_id if active else None, "activity_name": "室内平地慢走" if phase < 2 else "户外平地慢走", "activity_minutes": minutes, "weight_kg": weight, "note": "休息日也正常" if not active else "按能舒适交谈的节奏完成；示例记录"}


def half_year_case():
    days = (END - START).days + 1
    records = [case_day(i) for i in range(days)]
    phases = [
        {"month": "1 月", "title": "先看见习惯", "detail": "常有甜饮料、甜点和油炸肉；每周仅做几次 5 分钟慢走。"},
        {"month": "2 月", "title": "先替换一项", "detail": "早餐逐步减少甜点，午餐把油炸肉换成非油炸肉。"},
        {"month": "3 月", "title": "把规律建立起来", "detail": "加入燕麦、杂粮饭、豆腐和水果；步行增加到约 10—15 分钟。"},
        {"month": "4 月", "title": "增加蔬菜与步行", "detail": "多数正餐有蔬菜，步行约 15—20 分钟；仍有偶尔的甜点或油炸食物。"},
        {"month": "5 月", "title": "维持能做到的选择", "detail": "多数日子选择鱼、豆腐、蔬菜和水；步行频率提高。"},
        {"month": "6 月", "title": "把活动变成习惯", "detail": "每周约 5 天步行，每次约 25—30 分钟；仍保留休息日。"},
    ]
    return {"case_id": "fatty-liver-six-month-demo", "synthetic": True, "title": "林先生 · 脂肪肝生活方式记录（虚构）", "start": START.isoformat(), "end": END.isoformat(), "days": days, "profile": {"age": 42, "height_cm": 172, "conditions": ["脂肪肝", "血脂偏高"]}, "records": records, "phases": phases, "notice": "全部数据为教学虚构案例，不是患者病历或治疗结果。饮食分是系统演示分，体重与运动分钟为故事设定；没有肝功能、血脂或影像复查数据，不能推断脂肪肝已逆转。", "source_urls": ["https://www.niddk.nih.gov/health-information/liver-disease/nafld-nash/treatment", "https://www.cdc.gov/physical-activity-basics/adding-adults/index.html"]}
