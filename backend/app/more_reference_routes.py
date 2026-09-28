"""Local search over official food composition and health-topic snapshots."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .dependencies import db_session
from .models import FoodCompositionReference, HealthTopicReference
from .reference_zh import chinese_food_query, english_food_query, food_label

router = APIRouter(prefix="/reference", tags=["Reference data"])


@router.get("/composition")
def search_composition(q: str = Query(default="", max_length=100), kind: str = Query(default="", pattern="^(|foundation_food|sr_legacy_food)$"), limit: int = Query(default=20, ge=1, le=50), db: Session = Depends(db_session)):
    term = english_food_query(q)
    chinese_label = chinese_food_query(q)
    statement = select(FoodCompositionReference)
    if term:
        statement = statement.where(FoodCompositionReference.description_en.ilike(f"%{term}%"))
    if kind:
        statement = statement.where(FoodCompositionReference.data_type == kind)
    if chinese_label:
        candidates = db.scalars(statement.order_by(FoodCompositionReference.description_en, FoodCompositionReference.fdc_id)).all()
        matches = [row for row in candidates if food_label(row.description_en) == chinese_label]
        total, rows = len(matches), matches[:limit]
    else:
        total = db.scalar(select(func.count()).select_from(statement.subquery()))
        rows = db.scalars(statement.order_by(FoodCompositionReference.description_en, FoodCompositionReference.fdc_id).limit(limit)).all()
    fields = ("energy_kcal", "protein_g", "fat_g", "carbohydrate_g", "fiber_g", "sodium_mg")
    return {"items": [{"fdc_id": r.fdc_id, "name_zh": food_label(r.description_en), "description_en": r.description_en, "data_type": r.data_type, "release": r.release, "nutrients_per_100g": {field: getattr(r, field) for field in fields}, "source_url": r.source_url} for r in rows], "total": total, "scope_note": "中文名仅表示可识别的食物类别，详细品种与做法以英文原文为准。美国食品每100克参考值；缺失项为 null，不代表中国菜肴或实际食用量。"}


@router.get("/health-topics")
def search_health_topics(q: str = Query(default="", max_length=100), featured: bool = False, limit: int = Query(default=20, ge=1, le=50), db: Session = Depends(db_session)):
    term = q.strip().casefold()
    statement = select(HealthTopicReference)
    if featured:
        statement = statement.where(HealthTopicReference.title_zh.is_not(None))
    if term:
        statement = statement.where(HealthTopicReference.title_en.ilike(f"%{term}%") | HealthTopicReference.title_zh.ilike(f"%{term}%"))
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    rows = db.scalars(statement.order_by(HealthTopicReference.title_en).limit(limit)).all()
    return {"items": [{"topic_id": r.topic_id, "title_en": r.title_en, "title_zh": r.title_zh, "summary_en": r.summary_en, "condition_codes": r.condition_codes, "source_url": r.source_url, "release": r.release, "language": "English"} for r in rows], "total": total, "attribution": "Source: MedlinePlus, National Library of Medicine.", "scope_note": "英文健康科普资料；中文名称仅为本站检索辅助，不替代原文。"}
