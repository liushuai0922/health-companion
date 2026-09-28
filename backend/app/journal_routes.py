from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.activity.engine import exercise_catalog
from core.clock import local_today
from .case_study import half_year_case
from .dependencies import db_session, require_patient
from .models import DietLog, JournalLog, utc_now
from .schemas import InputModel


router = APIRouter(tags=["Daily journal"])


class JournalEntry(InputModel):
    day: date
    breakfast: str = Field(default="", max_length=300)
    lunch: str = Field(default="", max_length=300)
    dinner: str = Field(default="", max_length=300)
    snacks: str = Field(default="", max_length=300)
    activity_id: str | None = None
    activity_minutes: int = Field(default=0, ge=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=700, allow_inf_nan=False)
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_record(self):
        valid_ids = {activity["id"] for activity in exercise_catalog()["activities"]}
        if self.activity_id is not None and self.activity_id not in valid_ids:
            raise ValueError("未知运动项目")
        if bool(self.activity_id) != bool(self.activity_minutes):
            raise ValueError("运动项目和运动分钟数需要同时填写")
        if not any((self.breakfast.strip(), self.lunch.strip(), self.dinner.strip(), self.snacks.strip(), self.activity_minutes, self.weight_kg, self.notes.strip())):
            raise ValueError("请至少填写饮食、运动、体重或备注中的一项")
        return self


def journal_data(row, diet=None):
    return {"day": row.day.isoformat(), "entry": row.entry, "diet_score": diet.result.get("score") if diet else None, "saved_at": row.saved_at.isoformat()}


@router.get("/demo/half-year-case")
def get_half_year_case():
    return half_year_case()


@router.put("/patients/{patient_id}/journal-days/{day}")
def save_journal_day(patient_id: int, day: date, payload: JournalEntry, db: Session = Depends(db_session)):
    require_patient(db, patient_id)
    if day != payload.day:
        raise HTTPException(422, "请求日期与日志日期不一致")
    if day > local_today():
        raise HTTPException(422, "不能把未来计划保存为已完成日志")
    row = db.scalar(select(JournalLog).where(JournalLog.patient_id == patient_id, JournalLog.day == day))
    if row is None:
        row = JournalLog(patient_id=patient_id, day=day)
        db.add(row)
    row.entry = payload.model_dump(mode="json")
    row.saved_at = utc_now()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "该日日志发生冲突，请重新载入")
    db.refresh(row)
    diet = db.scalar(select(DietLog).where(DietLog.patient_id == patient_id, DietLog.day == day))
    return journal_data(row, diet)


@router.get("/patients/{patient_id}/journal-days/{day}")
def get_journal_day(patient_id: int, day: date, db: Session = Depends(db_session)):
    require_patient(db, patient_id)
    row = db.scalar(select(JournalLog).where(JournalLog.patient_id == patient_id, JournalLog.day == day))
    if row is None:
        raise HTTPException(404, "该日还没有综合日志")
    diet = db.scalar(select(DietLog).where(DietLog.patient_id == patient_id, DietLog.day == day))
    return journal_data(row, diet)


@router.get("/patients/{patient_id}/journal-days")
def list_journal_days(patient_id: int, limit: int = Query(default=180, ge=1, le=365), db: Session = Depends(db_session)):
    require_patient(db, patient_id)
    rows = db.scalars(select(JournalLog).where(JournalLog.patient_id == patient_id).order_by(JournalLog.day.desc()).limit(limit)).all()
    if not rows:
        return []
    diets = db.scalars(select(DietLog).where(DietLog.patient_id == patient_id, DietLog.day.in_([row.day for row in rows]))).all()
    by_day = {row.day: row for row in diets}
    return [journal_data(row, by_day.get(row.day)) for row in rows]
