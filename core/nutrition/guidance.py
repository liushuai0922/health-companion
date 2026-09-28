from core.disease.engine import catalog
from core.nutrition.engine import nutrition_plan
from core.rules import load_rules

TOPICS = {
 "added_sugar":("减少甜饮料与甜食","把甜饮料换成白水或无糖饮品，减少果汁和甜点。"),
 "saturated_fat":("减少高饱和脂肪食物","少选肥肉、黄油、油炸食品，使用适量植物油。"),
 "fiber":("增加蔬菜和富含纤维的食物","每餐加蔬菜，用适量全谷物替代部分精制主食。"),
 "sodium":("减少盐和高钠加工食品","少用浓重酱料，少选腌制肉，查看包装钠含量。"),
 "refined_carbohydrate":("关注主食种类与份量","全谷物可替代部分白米白面，但仍需留意总份量。"),
 "alcohol":("减少或避免饮酒","脂肪肝或痛风发作等情况需与医生确认更严格的安排。"),
 "high_purine_food":("减少高嘌呤动物性食物","少选动物内脏、浓肉汤和部分高嘌呤水产。"),
 "hydration":("饮水量先核对个体限制","心、肾功能异常或有限液要求时，不能套用一般饮水量。"),
}

def combined_guidance(conditions, preferences=None, allergies=None):
    active=sorted({c["disease_code"] for c in conditions if c["status"]=="active"})
    plan=nutrition_plan(conditions,preferences,allergies)
    names={code:item["name"] for code,item in catalog().items()}
    guide_mapping=load_rules("disease_guides.json")["disease_to_guide"]
    goals,review=[],[]
    for c in plan["constraints"]:
        key=c["constraint"]
        if key not in TOPICS: continue
        title,action=TOPICS[key]
        item={"topic":key,"title":title,"action":action,
              "diseases":[names.get(code,code) for code in c["sources"]],
              "source_urls":sorted({p["evidence_source"] for p in c["provenance"] if p["evidence_source"].startswith("https://")}),
              "shared":len({guide_mapping.get(source,source) for source in c["sources"]})>1,"needs_review":c["needs_review"]}
        (review if c["needs_review"] else goals).append(item)
    goals.sort(key=lambda x:(-len(x["diseases"]),list(TOPICS).index(x["topic"])))
    notes=[]
    uric=bool(set(active)&{"gout","hyperuricemia"})
    if uric and "hyperlipidemia" in active:
        notes.append("同时关注血脂和尿酸时，可考虑鸡蛋、低脂奶和适量豆腐等蛋白质来源；鱼和海鲜不能一概视作适合所有痛风阶段。")
    if uric and "type2_diabetes" in active:
        notes.append("同时关注血糖和尿酸时，主食不必全部取消；可选适量全谷物，并结合血糖记录调整份量。")
    if "type2_diabetes" in active:
        notes.append("已用降糖药时，进餐时间与血糖监测应遵循个人医嘱；本页不根据药名调整餐次或剂量。")
    if uric:
        notes.append("痛风／高尿酸血症的饮水建议以心、肾功能正常且无限液要求为前提；本系统不能判断个人可饮水量。")
    if "chronic_kidney_disease" in active:
        notes.append("慢性肾脏病的蛋白质、钾、磷和饮水目标需根据肾功能、透析情况与化验单制定；请勿直接套用其他疾病的高蛋白、高钾或大量饮水建议。")
    if "stroke" in active:
        notes.append("脑卒中后如有吞咽困难、呛咳或体重下降，应先做吞咽与营养评估，再确定食物质地。")
    if "sarcopenia" in active and "chronic_kidney_disease" in active:
        notes.append("肌少症与慢性肾脏病并存时，蛋白质目标需要医生和营养师共同确定。")
    if allergies:
        notes.append("已记录食物过敏；示例食物尚未做过敏安全核对。")
    meal="安排一餐时，先放入蔬菜，搭配适量主食与蛋白质食物；饮料优先白水或无糖饮品。"
    if "type2_diabetes" in active:
        meal="可用半盘非淀粉类蔬菜、四分之一盘富含纤维的主食、四分之一盘蛋白质作为起点；主食份量仍结合血糖和用药确认。"
    if uric:
        meal+=" 蛋白质可考虑鸡蛋、低脂奶和适量豆腐；动物内脏、浓肉汤及部分水产需限制。"
    if "hypertension" in active:
        meal+=" 烹调少盐，少用高钠酱料。"
    if "hyperlipidemia" in active or "fatty_liver" in active:
        meal+=" 少用肥肉和油炸做法，留意整体份量。"
    return {"diseases":[names.get(code,code) for code in active],
            "common_goals":[x for x in goals if x["shared"]],
            "specific_goals":[x for x in goals if not x["shared"]],
            "review_goals":review,"combination_notes":notes,"meal_approach":meal,
            "scope":"依据已记录疾病合并饮食方向，不制定个人热量、营养素或药物处方。"}

def selected_disease_guides(conditions):
    data=load_rules("disease_guides.json")
    selected={c["disease_code"] for c in conditions if c["status"]=="active"}
    keys=dict.fromkeys(data["disease_to_guide"][code] for code in sorted(selected) if code in data["disease_to_guide"])
    return [{"key":key,**data["guides"][key]} for key in keys]
