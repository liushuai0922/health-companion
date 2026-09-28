"""Create one explicitly fictional profile. Does not replace existing records."""
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from backend.app.database import Base, make_engine, session_factory
from backend.app.models import Patient, Condition, Medication, Observation
from backend.app.schemas import PatientCreate, MedicationCreate, ObservationCreate
from core.clock import LOCAL_TIMEZONE, local_today
from core.disease.engine import catalog

DEMO_NAME = "林先生（脂肪肝演示）"


def seed_demo(sessions, interaction_demo=False):
    demo_name = "虚拟演示用户（非真实处方）" if interaction_demo else DEMO_NAME
    with sessions.begin() as db:
        existing = db.scalar(select(Patient).where(Patient.name == demo_name))
        if existing:
            return existing.id
        profile = PatientCreate(name=demo_name, age=42, sex="male", height_cm=172, weight_kg=82, dietary_preferences=["清淡", "体重管理"], allergies=[])
        patient = Patient(**profile.model_dump())
        db.add(patient)
        db.flush()
        for code in (["hypertension", "type2_diabetes", "hyperlipidemia"] if interaction_demo else ["hyperlipidemia", "fatty_liver"]):
            db.add(Condition(patient_id=patient.id, disease_code=code, disease_name=catalog()[code]["name"], status="active", severity="unspecified", notes="虚构记录，仅用于验证规则命中。"))
        medication_examples = [
            ("阿托伐他汀（演示）", "atorvastatin", 10, "21:00", "anytime"),
            ("布洛芬（演示）", "ibuprofen", 200, "08:30", "after_meal"),
            ("华法林（演示）", "warfarin", 2.5, "21:00", "anytime"),
            ("阿托伐他汀重复记录（演示）", "阿托伐他汀钙片", 10, "21:00", "anytime"),
        ] if interaction_demo else []
        for name, code, dose, time, meal in medication_examples:
            payload = MedicationCreate(drug_name=name, generic_name=code, dose=dose, unit="mg", administration_time=[time], meal_relation=meal, start_date=local_today(), indication="虚构测试数据，故意包含风险与重复记录，不是服药建议。")
            db.add(Medication(patient_id=patient.id, **payload.model_dump()))
        if interaction_demo:
            observation = ObservationCreate(metric_type="blood_pressure", systolic=125, diastolic=80, unit="mmHg", measured_at=datetime.now(LOCAL_TIMEZONE), notes="虚拟测量值。")
            db.add(Observation(patient_id=patient.id, **observation.model_dump()))
        return patient.id


if __name__ == "__main__":
    engine = make_engine()
    Base.metadata.create_all(engine)
    patient_id = seed_demo(session_factory(engine))
    engine.dispose()
    print(f"Demo patient ID: {patient_id}")
    print("Demo: age 42, height 172 cm, weight 82 kg, hyperlipidemia and fatty liver; no prescribed medication assumed.")
