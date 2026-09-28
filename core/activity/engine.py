from core.rules import load_rules


def exercise_catalog():
    return load_rules("exercise_catalog.json")


def beginner_exercise_plan(profile, conditions):
    catalog = exercise_catalog()
    codes = {c["disease_code"] for c in conditions if c["status"] == "active"}
    notes = []
    if profile["age"] < 18:
        return {"available": False, "reason": "当前活动示例只面向成年人；儿童青少年需要适龄方案。", "activities": [], "week": [], "notes": [], "sources": catalog["sources"], "catalog_version": catalog["version"]}
    if codes:
        notes.append({"title": "先确认个人可活动范围", "text": "已记录慢性疾病。开始新的运动安排前，向医生确认适合你的活动种类和时长；这里没有检查心肺能力、血压、关节状况或禁忌证。", "source_url": "https://www.cdc.gov/physical-activity-basics/adding-adults/index.html"})
    if "type2_diabetes" in codes:
        notes.append({"title": "糖尿病与低血糖", "text": "如果使用胰岛素或促胰岛素分泌的药物，运动前后可能需要监测血糖，并与医疗团队确认低血糖处理；不要自行调整药量。", "source_url": "https://diabetes.org/health-wellness/fitness/blood-glucose-and-exercise"})
    if "chronic_kidney_disease" in codes:
        notes.append({"title": "慢性肾脏病", "text": "若目前活动很少，先向医生确认适合的活动类型和量；饮水与强度也要遵守个人限制。", "source_url": "https://www.niddk.nih.gov/health-information/kidney-disease/chronic-kidney-disease-ckd/managing"})
    if "gout" in codes:
        notes.append({"title": "痛风发作时", "text": "本示例适用于非急性发作时。若关节正红肿疼痛，暂缓给患处负重，先联系医生确认何时恢复活动。", "source_url": "https://www.arthritis.org/health-wellness/treatment/treatment-plan/disease-management/treatments-for-gout"})
    if "stroke" in codes or "osteoporosis" in codes or profile["age"] >= 65:
        notes.append({"title": "稳定与防跌倒", "text": "先用结实椅子或扶手辅助。若有跌倒史、卒中后运动障碍或骨折风险，动作和站立练习应由专业人员评估。", "source_url": "https://www.cdc.gov/physical-activity-basics/adding-older-adults/index.html"})
    if "fatty_liver" in codes:
        notes.append({"title": "脂肪肝", "text": "规律身体活动即使体重尚未变化也有益；不需要一开始就做高强度运动。", "source_url": "https://www.niddk.nih.gov/health-information/liver-disease/nafld-nash/treatment"})
    notes.append({"title": "何时停止", "text": "活动时出现胸痛、明显头晕、快要昏厥或异常气短，应停止活动并及时就医。", "source_url": "https://www.nhlbi.nih.gov/health/heart/physical-activity/risks"})
    activities = catalog["activities"]
    starter_ids = ["indoor_walk", "gentle_stretch", "wall_push"]
    if profile["age"] >= 65 or "stroke" in codes or "osteoporosis" in codes:
        starter_ids = ["indoor_walk", "seated_mobility", "supported_balance"]
    by_id = {activity["id"]: activity for activity in activities}
    week = [
        {"day": "周一", "items": ["indoor_walk", "gentle_stretch"]},
        {"day": "周二", "items": ["seated_mobility", "wall_push"]},
        {"day": "周三", "items": ["indoor_walk"]},
        {"day": "周四", "items": ["gentle_stretch", "supported_balance"]},
        {"day": "周五", "items": ["indoor_walk", "wall_push"]},
        {"day": "周六", "items": ["slow_walk"]},
        {"day": "周日", "items": []},
    ]
    if profile["age"] >= 65 or "stroke" in codes:
        for day in week:
            day["items"] = ["seated_mobility" if item == "slow_walk" else item for item in day["items"]]
    return {"available": True, "scope": "第一周低强度起步示例；可按体力缩短或休息，不要求一周内达到成人每周 150 分钟的长期目标。", "activities": activities, "recommended": starter_ids, "week": [{"day": day["day"], "items": [{"id": key, "name": by_id[key]["name"], "start": by_id[key]["start"]} for key in day["items"]]} for day in week], "notes": notes, "sources": catalog["sources"], "catalog_version": catalog["version"], "intensity_note": "以能舒适说话、感觉轻松为起点；MET 只是活动分类平均值，不代表你的实际强度。"}
