from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .dependencies import db_session
from .models import DrugReference, FoodReference, GuidelineReference, PurineReference, FoodCompositionReference, HealthTopicReference
from .reference_zh import SOURCE_NAMES, chinese_food_query, english_food_query, food_label

router = APIRouter(prefix="/reference", tags=["Reference data"])


def drug_data(row):
    return {"key": row.key, "name_zh": row.name_zh, "name_en": row.name_en, "group": row.group_name, "aliases": row.aliases, "rxcui": row.rxcui,
            "rxnorm_url": f"https://rxnav.nlm.nih.gov/REST/rxcui/{row.rxcui}/properties.json",
            "dailymed_label_title": row.dailymed_title,
            "dailymed_label_url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={row.dailymed_setid}" if row.dailymed_setid else None,
            "synced_at": row.synced_at.isoformat(),
            "note": "仅供核对药名与查看原始说明书，不表示推荐此药或已完成相互作用检查。"}


def food_data(row):
    return {"key": row.key, "fdc_id": row.fdc_id, "name_zh": food_label(row.description_en), "description_en": row.description_en, "data_type": row.data_type,
            "source_url": f"https://fdc.nal.usda.gov/food-details/{row.fdc_id}/nutrients",
            "synced_at": row.synced_at.isoformat(),
            "note": "美国食品参考条目，仅用于查看来源；不代表用户输入的菜肴、品牌或份量。"}


@router.get("/sources")
def source_status(db: Session = Depends(db_session)):
    drugs = db.scalars(select(DrugReference)).all()
    foods = db.scalars(select(FoodReference)).all()
    guidelines = db.scalars(select(GuidelineReference)).all()
    purines = db.scalars(select(PurineReference)).all()
    legacy_count = db.scalar(select(func.count()).select_from(FoodCompositionReference).where(FoodCompositionReference.data_type == "sr_legacy_food"))
    foundation_count = db.scalar(select(func.count()).select_from(FoodCompositionReference).where(FoodCompositionReference.data_type == "foundation_food"))
    topic_count = db.scalar(select(func.count()).select_from(HealthTopicReference))
    result = {
        "sources": [
            {"name": "RxNorm", "records": len(drugs), "purpose": "药物名称与 RxCUI 编码", "url": "https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html", "last_synced": max((r.synced_at for r in drugs), default=None)},
            {"name": "DailyMed", "records": sum(r.dailymed_setid is not None for r in drugs), "purpose": "药品说明书索引", "url": "https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm", "last_synced": max((r.synced_at for r in drugs if r.dailymed_setid), default=None)},
            {"name": "USDA FoodData Central", "records": len(foods), "purpose": "食品参考样本", "url": "https://fdc.nal.usda.gov/api-guide/", "last_synced": max((r.synced_at for r in foods), default=None)},
            {"name": "国家卫健委食养指南", "records": len(guidelines), "purpose": "糖尿病、高血压、肾病及老年相关疾病的官方文件索引", "url": "https://www.nhc.gov.cn/sps/c100088/list.shtml", "last_synced": max((r.synced_at for r in guidelines), default=None)},
            {"name": "USDA/ODS 食物嘌呤", "records": len(purines), "purpose": "食品与酒类样本值；不能直接推算个人摄入或痛风风险", "url": "https://www.ars.usda.gov/northeast-area/beltsville-md-bhnrc/beltsville-human-nutrition-research-center/methods-and-application-of-food-composition-laboratory/mafcl-site-pages/purine-content-of-foods/", "last_synced": max((r.synced_at for r in purines), default=None)},
            {"name": "USDA SR Legacy 全目录", "records": legacy_count, "purpose": "美国历史食品成分目录及部分每100克营养数据", "url": "https://fdc.nal.usda.gov/download-datasets/", "last_synced": db.scalar(select(func.max(FoodCompositionReference.synced_at)).where(FoodCompositionReference.data_type == "sr_legacy_food"))},
            {"name": "USDA Foundation Foods", "records": foundation_count, "purpose": "美国基础食品样本及部分每100克营养数据", "url": "https://fdc.nal.usda.gov/download-datasets/", "last_synced": db.scalar(select(func.max(FoodCompositionReference.synced_at)).where(FoodCompositionReference.data_type == "foundation_food"))},
            {"name": "MedlinePlus 健康主题", "records": topic_count, "purpose": "美国国家医学图书馆英文健康主题索引", "url": "https://medlineplus.gov/xml.html", "last_synced": db.scalar(select(func.max(HealthTopicReference.synced_at)))}
        ],
        "runtime": "本地 SQLite 快照；普通查询不请求外部服务。",
        "clinical_scope": "这些目录数据不扩大安全规则覆盖范围，也不自动生成药物风险判断。"
    }
    for source in result["sources"]:
        source["name_zh"] = SOURCE_NAMES.get(source["name"], source["name"])
    return result


@router.get("/drugs")
def search_drugs(q: str = Query(default="", max_length=100), limit: int = Query(default=15, ge=1, le=50), db: Session = Depends(db_session)):
    term = q.strip().casefold()
    rows = db.scalars(select(DrugReference).order_by(DrugReference.group_name, DrugReference.name_zh)).all()
    matches = [r for r in rows if not term or any(term in text.casefold() for text in [r.key, r.name_zh, r.name_en, *r.aliases])]
    return {"items": [drug_data(r) for r in matches[:limit]], "total": len(matches), "coverage_note": "药品名检索仅帮助填写；安全提醒仍来自独立的确定性规则。"}


@router.get("/foods")
def search_foods(q: str = Query(default="", max_length=100), limit: int = Query(default=15, ge=1, le=50), db: Session = Depends(db_session)):
    term = q.strip().casefold()
    rows = db.scalars(select(FoodReference).order_by(FoodReference.key)).all()
    english = english_food_query(term)
    chinese_label = chinese_food_query(q)
    matches = [r for r in rows if not term or (food_label(r.description_en) == chinese_label if chinese_label else term in r.key.casefold() or english in r.description_en.casefold())]
    return {"items": [food_data(r) for r in matches[:limit]], "total": len(matches)}


@router.get("/guidelines")
def search_guidelines(q: str = Query(default="", max_length=100), condition: str = Query(default="", max_length=100), limit: int = Query(default=30, ge=1, le=100), db: Session = Depends(db_session)):
    term = q.strip().casefold()
    code = condition.strip()
    rows = db.scalars(select(GuidelineReference).order_by(GuidelineReference.year.desc(), GuidelineReference.key)).all()
    matches = [r for r in rows if (not code or code in r.condition_codes) and (not term or term in r.title.casefold() or term in r.key.casefold())]
    return {"items": [{"key": r.key, "title": r.title, "publisher": r.publisher, "year": r.year, "condition_codes": r.condition_codes, "source_url": r.source_url, "note": r.note} for r in matches[:limit]], "total": len(matches), "scope_note": "官方文件索引；具体建议请查看原文。"}


@router.get("/purines")
def search_purines(q: str = Query(default="", max_length=100), limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(db_session)):
    term = english_food_query(q)
    chinese_label = chinese_food_query(q)
    query = select(PurineReference)
    if term:
        query = query.where(PurineReference.food_name_en.ilike(f"%{term}%"))
    if chinese_label:
        matches = [r for r in db.scalars(query.order_by(PurineReference.food_name_en, PurineReference.key)).all() if food_label(r.food_name_en) == chinese_label]
        total, rows = len(matches), matches[:limit]
    else:
        rows = db.scalars(query.order_by(PurineReference.food_name_en, PurineReference.key).limit(limit)).all()
        total = db.query(PurineReference).filter(PurineReference.food_name_en.ilike(f"%{term}%")).count() if term else db.query(PurineReference).count()
    return {"items": [{"key": r.key, "food_name_zh": food_label(r.food_name_en), "food_name_en": r.food_name_en, "category": r.category, "total_purines_mg": round(r.total_purines_mg, 2), "unit": r.unit, "sample_n": r.sample_n, "year": r.year, "source_code": r.source_code, "country": r.country, "source_url": r.source_url} for r in rows], "total": total, "scope_note": "中文名称仅为食物类别检索词，品种和生熟状态请核对英文原文；原始样本不参与日记评分，也不能判断个人痛风风险。"}
