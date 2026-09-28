from fastapi import HTTPException, Request
from .models import Patient


def db_session(request: Request):
    with request.app.state.sessions() as session:
        yield session


def require_patient(db, patient_id):
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(404, "Patient not found")
    return patient
