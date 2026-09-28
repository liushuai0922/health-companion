from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from core.disease.engine import catalog
from core.nutrition.engine import nutrition_plan
from core.medication.engine import medication_plan, is_scheduled
from core.interactions.engine import safety_check, read_catalog
from core.care_plan.engine import generate_care_plan
from core.clock import local_today
from .database import Base, make_engine, session_factory
from .models import Patient, Condition, Medication, MedicationEvent, Observation
from .schemas import PatientCreate, PatientRead, ConditionCreate, ConditionRead, MedicationCreate, MedicationRead, MedicationEventCreate, MedicationEventRead, ObservationCreate, ObservationRead, METRIC_UNITS
from .dependencies import db_session, require_patient
from .diet_routes import router as diet_router
from .reference_routes import router as reference_router
from .more_reference_routes import router as more_reference_router
from .journal_routes import router as journal_router


class HealthResponse(BaseModel):
    status: str


def create_app(database_url=None):
    @asynccontextmanager
    async def lifespan(app):
        engine = make_engine(database_url)
        Base.metadata.create_all(engine)
        app.state.sessions = session_factory(engine)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Health Companion API", version="0.3.0", lifespan=lifespan, docs_url=None, redoc_url=None, description="本地演示后端。规则仅供功能验证；不诊断疾病，不自动调整用药。日期默认 UTC+08:00。")
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def local_home():
        return FileResponse(static_dir / "index.html")

    @app.get("/docs", include_in_schema=False)
    def offline_docs():
        return get_swagger_ui_html(openapi_url="/openapi.json", title="Health Companion API", swagger_js_url="/static/swagger-ui-bundle.js", swagger_css_url="/static/swagger-ui.css", swagger_favicon_url="/static/favicon.svg", swagger_ui_parameters={"validatorUrl": None, "persistAuthorization": False})

    @app.get("/demo-info", tags=["Demo"])
    def demo_info(db: Session = Depends(db_session)):
        patient = db.scalar(select(Patient).where(Patient.name == "林先生（脂肪肝演示）"))
        return {"patient_id": patient.id if patient else None, "demo": True, "notice": "虚拟数据，非真实处方。"}

    @app.get("/patients", response_model=list[PatientRead], tags=["Patients"])
    def list_patients(db: Session = Depends(db_session)):
        return db.scalars(select(Patient).order_by(Patient.id)).all()

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    def health():
        return HealthResponse(status="ok")

    @app.post("/patients", response_model=PatientRead, status_code=201, tags=["Patients"])
    def create_patient(payload: PatientCreate, db: Session = Depends(db_session)):
        patient = Patient(**payload.model_dump())
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    @app.get("/patients/{patient_id}", response_model=PatientRead, tags=["Patients"])
    def read_patient(patient_id: int, db: Session = Depends(db_session)):
        return require_patient(db, patient_id)

    @app.get("/catalog/diseases", tags=["Catalog"])
    def disease_catalog():
        return catalog()

    @app.post("/patients/{patient_id}/conditions", response_model=ConditionRead, status_code=201, tags=["Diseases"])
    def add_condition(patient_id: int, payload: ConditionCreate, db: Session = Depends(db_session)):
        require_patient(db, patient_id)
        rule = catalog().get(payload.disease_code)
        if rule is None:
            raise HTTPException(422, "Disease code is not supported by the current rule catalog")
        condition = Condition(patient_id=patient_id, disease_name=rule["name"], **payload.model_dump())
        db.add(condition)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "This condition is already recorded")
        db.refresh(condition)
        return condition

    @app.get("/patients/{patient_id}/conditions", response_model=list[ConditionRead], tags=["Diseases"])
    def list_conditions(patient_id: int, db: Session = Depends(db_session)):
        require_patient(db, patient_id)
        return db.scalars(select(Condition).where(Condition.patient_id == patient_id).order_by(Condition.id)).all()

    @app.get("/patients/{patient_id}/nutrition-constraints", tags=["Nutrition"])
    def nutrition(patient_id: int, db: Session = Depends(db_session)):
        patient = require_patient(db, patient_id)
        conditions = db.scalars(select(Condition).where(Condition.patient_id == patient_id)).all()
        return nutrition_plan([{"disease_code": c.disease_code, "status": c.status} for c in conditions], patient.dietary_preferences, patient.allergies)

    def owned_medication(db, patient_id, medication_id):
        require_patient(db, patient_id)
        med = db.get(Medication, medication_id)
        if med is None or med.patient_id != patient_id:
            raise HTTPException(404, "Medication not found")
        return med

    @app.post("/patients/{patient_id}/medications", response_model=MedicationRead, status_code=201, tags=["Medications"])
    def add_medication(patient_id: int, payload: MedicationCreate, db: Session = Depends(db_session)):
        require_patient(db, patient_id)
        med = Medication(patient_id=patient_id, **payload.model_dump())
        db.add(med)
        db.commit()
        db.refresh(med)
        return med

    @app.get("/patients/{patient_id}/medications", response_model=list[MedicationRead], tags=["Medications"])
    def list_medications(patient_id: int, active_only: bool = True, db: Session = Depends(db_session)):
        require_patient(db, patient_id)
        query = select(Medication).where(Medication.patient_id == patient_id)
        if active_only:
            query = query.where(Medication.active.is_(True))
        return db.scalars(query.order_by(Medication.id)).all()

    @app.put("/patients/{patient_id}/medications/{medication_id}", response_model=MedicationRead, tags=["Medications"])
    def update_medication(patient_id: int, medication_id: int, payload: MedicationCreate, db: Session = Depends(db_session)):
        med = owned_medication(db, patient_id, medication_id)
        for key, value in payload.model_dump().items():
            setattr(med, key, value)
        db.commit()
        db.refresh(med)
        return med

    @app.post("/patients/{patient_id}/medications/{medication_id}/deactivate", response_model=MedicationRead, tags=["Medications"])
    def deactivate_medication(patient_id: int, medication_id: int, db: Session = Depends(db_session)):
        med = owned_medication(db, patient_id, medication_id)
        med.active = False
        db.commit()
        return med

    @app.put("/patients/{patient_id}/medications/{medication_id}/events", response_model=MedicationEventRead, tags=["Medications"])
    def record_event(patient_id: int, medication_id: int, payload: MedicationEventCreate, db: Session = Depends(db_session)):
        med = owned_medication(db, patient_id, medication_id)
        snapshot = MedicationRead.model_validate(med).model_dump(mode="json")
        if not is_scheduled(snapshot, payload.scheduled_date) or payload.scheduled_time not in med.administration_time:
            raise HTTPException(422, "No scheduled dose exists at that date/time")
        event = db.scalar(select(MedicationEvent).where(MedicationEvent.medication_id == medication_id, MedicationEvent.scheduled_date == payload.scheduled_date, MedicationEvent.scheduled_time == payload.scheduled_time))
        if event is None:
            event = MedicationEvent(patient_id=patient_id, medication_id=medication_id, medication_snapshot=snapshot, **payload.model_dump())
            db.add(event)
        else:
            for key, value in payload.model_dump().items():
                setattr(event, key, value)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Dose record changed concurrently; reload and retry")
        db.refresh(event)
        return event

    @app.get("/patients/{patient_id}/medication-history", response_model=list[MedicationEventRead], tags=["Medications"])
    def medication_history(patient_id: int, db: Session = Depends(db_session)):
        require_patient(db, patient_id)
        return db.scalars(select(MedicationEvent).where(MedicationEvent.patient_id == patient_id).order_by(MedicationEvent.scheduled_date.desc(), MedicationEvent.scheduled_time.desc(), MedicationEvent.id.desc())).all()

    @app.get("/patients/{patient_id}/medication-plan", tags=["Medications"])
    def daily_medications(patient_id: int, day: date | None = None, db: Session = Depends(db_session)):
        require_patient(db, patient_id)
        meds = db.scalars(select(Medication).where(Medication.patient_id == patient_id)).all()
        events = db.scalars(select(MedicationEvent).where(MedicationEvent.patient_id == patient_id)).all()
        return {"date": (day or local_today()).isoformat(), "items": medication_plan([MedicationRead.model_validate(m).model_dump(mode="json") for m in meds], day or local_today(), [MedicationEventRead.model_validate(e).model_dump(mode="json") for e in events])}

    @app.get("/catalog/drugs", tags=["Catalog"])
    def drugs():
        return read_catalog("drugs")

    @app.get("/catalog/foods", tags=["Catalog"])
    def foods_catalog():
        return read_catalog("foods")

    @app.get("/patients/{patient_id}/safety-check", tags=["Safety"])
    def check_safety(patient_id: int, day: date | None = None, foods: list[str] | None = Query(default=None), db: Session = Depends(db_session)):
        require_patient(db, patient_id)
        conditions = db.scalars(select(Condition).where(Condition.patient_id == patient_id)).all()
        medications = db.scalars(select(Medication).where(Medication.patient_id == patient_id)).all()
        return safety_check([ConditionRead.model_validate(c).model_dump(mode="json") for c in conditions], [MedicationRead.model_validate(m).model_dump(mode="json") for m in medications], day or local_today(), foods)

    @app.get("/catalog/observation-types", tags=["Catalog"])
    def observation_types():
        return METRIC_UNITS

    @app.post("/patients/{patient_id}/observations", response_model=ObservationRead, status_code=201, tags=["Observations"])
    def add_observation(patient_id: int, payload: ObservationCreate, db: Session = Depends(db_session)):
        require_patient(db, patient_id)
        observation = Observation(patient_id=patient_id, **payload.model_dump())
        db.add(observation)
        db.commit()
        db.refresh(observation)
        return observation

    @app.get("/patients/{patient_id}/observations", response_model=list[ObservationRead], tags=["Observations"])
    def list_observations(patient_id: int, db: Session = Depends(db_session)):
        require_patient(db, patient_id)
        return db.scalars(select(Observation).where(Observation.patient_id == patient_id).order_by(Observation.measured_at.desc(), Observation.id.desc())).all()

    @app.get("/patients/{patient_id}/care-plan", tags=["Care Plan"])
    def care_plan(patient_id: int, day: date | None = None, foods: list[str] | None = Query(default=None), db: Session = Depends(db_session)):
        patient = require_patient(db, patient_id)
        def records(model, schema):
            rows = db.scalars(select(model).where(model.patient_id == patient_id).order_by(model.id)).all()
            return [schema.model_validate(row).model_dump(mode="json") for row in rows]
        return generate_care_plan(PatientRead.model_validate(patient).model_dump(mode="json"), records(Condition, ConditionRead), records(Medication, MedicationRead), records(Observation, ObservationRead), records(MedicationEvent, MedicationEventRead), day or local_today(), foods)

    app.include_router(diet_router)
    app.include_router(reference_router)
    app.include_router(more_reference_router)
    app.include_router(journal_router)
    return app


app = create_app()
