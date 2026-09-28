from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .dependencies import db_session, require_patient
from .diet_schemas import Intake, DietDay
from .models import Condition, DietLog, Medication, Patient, utc_now
from .schemas import PatientRead, ConditionRead, MedicationRead
from core.clock import local_today
from core.rules import load_rules
from core.disease.engine import catalog
from core.nutrition.engine import nutrition_plan
from core.nutrition.guidance import combined_guidance, selected_disease_guides
from core.nutrition.scoring import diet_catalog, score_day
from core.activity.engine import exercise_catalog, beginner_exercise_plan
from core.interactions.engine import safety_check

router = APIRouter(tags=["Diet experience"])


def profile_data(db, patient_id):
    patient = require_patient(db, patient_id)
    conditions = db.scalars(select(Condition).where(Condition.patient_id == patient_id).order_by(Condition.id)).all()
    meds = db.scalars(select(Medication).where(Medication.patient_id == patient_id, Medication.active.is_(True)).order_by(Medication.id)).all()
    return {"patient": PatientRead.model_validate(patient).model_dump(mode="json"), "conditions": [ConditionRead.model_validate(c).model_dump(mode="json") for c in conditions], "medications": [MedicationRead.model_validate(m).model_dump(mode="json") for m in meds]}


def save_profile(db, payload, patient_id=None):
    # Validate ownership before changing any persisted data.
    patient = require_patient(db, patient_id) if patient_id else None
    existing_meds = {m.id: m for m in db.scalars(select(Medication).where(Medication.patient_id == patient_id)).all()} if patient else {}
    if any(m.id is not None and m.id not in existing_meds for m in payload.medications):
        raise HTTPException(422, "药物记录不属于当前资料")
    if patient is None:
        patient = Patient(**payload.patient.model_dump())
        db.add(patient)
        db.flush()
    else:
        for key, value in payload.patient.model_dump().items():
            setattr(patient, key, value)
    existing_conditions = {c.disease_code: c for c in db.scalars(select(Condition).where(Condition.patient_id == patient.id)).all()}
    for code, condition in existing_conditions.items():
        condition.status = "active" if code in payload.conditions else "inactive"
    for code in payload.conditions:
        if code not in existing_conditions:
            db.add(Condition(patient_id=patient.id, disease_code=code, disease_name=catalog()[code]["name"], status="active", severity="unspecified", notes="用户在资料页记录"))
    selected_ids = {m.id for m in payload.medications if m.id is not None}
    for med_id, med in existing_meds.items():
        if med_id not in selected_ids:
            med.active = False
    for data in payload.medications:
        values = data.model_dump(exclude={"id"})
        if data.id is None:
            db.add(Medication(patient_id=patient.id, **values))
        else:
            for key, value in values.items():
                setattr(existing_meds[data.id], key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "资料发生冲突，请刷新后重试")
    return profile_data(db, patient.id)


@router.post("/intake", status_code=201)
def create_intake(payload: Intake, db: Session = Depends(db_session)):
    return save_profile(db, payload)


@router.put("/patients/{patient_id}/intake")
def update_intake(patient_id: int, payload: Intake, db: Session = Depends(db_session)):
    return save_profile(db, payload, patient_id)


@router.get("/patients/{patient_id}/intake")
def get_intake(patient_id: int, db: Session = Depends(db_session)):
    return profile_data(db, patient_id)


@router.get("/catalog/gout-guide")
def get_gout_guide():
    return load_rules("gout_guide.json")


@router.get("/catalog/health-literacy")
def get_health_literacy():
    return load_rules("health_literacy.json")


@router.get("/catalog/diet-foods")
def get_food_catalog():
    return diet_catalog()


@router.get("/catalog/exercises")
def get_exercise_catalog():
    return exercise_catalog()


@router.get("/patients/{patient_id}/diet-guide")
def get_diet_guide(patient_id: int, db: Session = Depends(db_session)):
    profile = profile_data(db, patient_id)
    patient = profile["patient"]
    return {**profile, "nutrition": nutrition_plan(profile["conditions"], patient["dietary_preferences"], patient["allergies"]), "combined_guidance": combined_guidance(profile["conditions"], patient["dietary_preferences"], patient["allergies"]), "disease_guides": selected_disease_guides(profile["conditions"]), "exercise": beginner_exercise_plan(patient, profile["conditions"]), "safety": safety_check(profile["conditions"], profile["medications"], local_today()), "weight_note": "BMI 是身高体重的计算指标，不单独判断病情。若已确认需要减重，和专业人员一起逐步调整饮食，不追求快速减重。", "scope_note": "以下为成人饮食方向参考；脂肪肝类型、特殊人群和个体限制仍需确认。"}


def log_data(log):
    return {"id": log.id, "patient_id": log.patient_id, "day": log.day.isoformat(), "diary": log.diary, "result": log.result, "profile_snapshot": log.profile_snapshot, "saved_at": log.saved_at.isoformat()}


@router.put("/patients/{patient_id}/diet-days/{day}")
def save_diet_day(patient_id: int, day: date, payload: DietDay, db: Session = Depends(db_session)):
    profile = profile_data(db, patient_id)
    if day != payload.day:
        raise HTTPException(422, "请求日期与记录日期不一致")
    if day > local_today():
        raise HTTPException(422, "暂不能把未来计划保存为已吃的饮食记录")
    diary = payload.model_dump(mode="json")
    result = score_day(profile["patient"], profile["conditions"], diary)
    food_map = {food["id"]: food for food in diet_catalog()["foods"]}
    exposures = set()
    for meal in diary["meals"]:
        for food in meal["items"]:
            if food["food_id"] == "grapefruit":
                exposures.add("grapefruit")
            if "high_sodium" in food_map[food["food_id"]]["tags"]:
                exposures.add("high_sodium_food")
    result["safety"] = safety_check(profile["conditions"], profile["medications"], day, sorted(exposures))
    row = db.scalar(select(DietLog).where(DietLog.patient_id == patient_id, DietLog.day == day))
    if row is None:
        row = DietLog(patient_id=patient_id, day=day)
        db.add(row)
    row.diary, row.result, row.profile_snapshot, row.saved_at = diary, result, profile, utc_now()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "当天记录已被更新，请重新载入后保存")
    db.refresh(row)
    return log_data(row)


@router.get("/patients/{patient_id}/diet-days/{day}")
def get_diet_day(patient_id: int, day: date, db: Session = Depends(db_session)):
    require_patient(db, patient_id)
    row = db.scalar(select(DietLog).where(DietLog.patient_id == patient_id, DietLog.day == day))
    if row is None:
        raise HTTPException(404, "当天还没有饮食记录")
    return log_data(row)


@router.get("/patients/{patient_id}/diet-days")
def list_diet_days(patient_id: int, db: Session = Depends(db_session)):
    require_patient(db, patient_id)
    rows = db.scalars(select(DietLog).where(DietLog.patient_id == patient_id).order_by(DietLog.day.desc()).limit(30)).all()
    return [{"day": row.day.isoformat(), "score": row.result["score"], "saved_at": row.saved_at.isoformat()} for row in rows]
