from datetime import date, datetime, timezone
from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base, UTCDateTime


def utc_now():
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(20))
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    allergies: Mapped[list] = mapped_column(JSON, default=list)
    dietary_preferences: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    @property
    def bmi(self):
        return round(self.weight_kg / (self.height_cm / 100) ** 2, 2)


class Condition(Base):
    __tablename__ = "conditions"
    __table_args__ = (UniqueConstraint("patient_id", "disease_code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    disease_code: Mapped[str] = mapped_column(String(100))
    disease_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    diagnosis_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    severity: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str] = mapped_column(String(2000))


class Medication(Base):
    __tablename__ = "medications"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    drug_name: Mapped[str] = mapped_column(String(100))
    generic_name: Mapped[str] = mapped_column(String(100))
    dose: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30))
    route: Mapped[str] = mapped_column(String(30))
    frequency: Mapped[str] = mapped_column(String(30))
    administration_time: Mapped[list] = mapped_column(JSON)
    meal_relation: Mapped[str] = mapped_column(String(30))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    indication: Mapped[str] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MedicationEvent(Base):
    __tablename__ = "medication_events"
    __table_args__ = (UniqueConstraint("medication_id", "scheduled_date", "scheduled_time"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    medication_id: Mapped[int] = mapped_column(ForeignKey("medications.id"), index=True)
    scheduled_date: Mapped[date] = mapped_column(Date)
    scheduled_time: Mapped[str] = mapped_column(String(5))
    status: Mapped[str] = mapped_column(String(20))
    taken_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    delayed_to: Mapped[str | None] = mapped_column(String(5), nullable=True)
    notes: Mapped[str] = mapped_column(String(1000))
    medication_snapshot: Mapped[dict] = mapped_column(JSON)
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class DietLog(Base):
    __tablename__ = "diet_logs"
    __table_args__ = (UniqueConstraint("patient_id", "day"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    diary: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    profile_snapshot: Mapped[dict] = mapped_column(JSON)
    saved_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class JournalLog(Base):
    __tablename__ = "journal_logs"
    __table_args__ = (UniqueConstraint("patient_id", "day"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    entry: Mapped[dict] = mapped_column(JSON)
    saved_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class DrugReference(Base):
    __tablename__ = "drug_references"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    name_zh: Mapped[str] = mapped_column(String(100))
    name_en: Mapped[str] = mapped_column(String(100))
    group_name: Mapped[str] = mapped_column(String(60))
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    rxcui: Mapped[str] = mapped_column(String(30))
    dailymed_setid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dailymed_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class FoodReference(Base):
    __tablename__ = "food_references"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    fdc_id: Mapped[int] = mapped_column(Integer, unique=True)
    description_en: Mapped[str] = mapped_column(String(500))
    data_type: Mapped[str] = mapped_column(String(50))
    synced_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class Observation(Base):
    __tablename__ = "observations"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    metric_type: Mapped[str] = mapped_column(String(50))
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    systolic: Mapped[float | None] = mapped_column(Float, nullable=True)
    diastolic: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(30))
    measured_at: Mapped[datetime] = mapped_column(UTCDateTime)
    notes: Mapped[str] = mapped_column(String(1000))


class GuidelineReference(Base):
    __tablename__ = "guideline_references"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    publisher: Mapped[str] = mapped_column(String(100))
    year: Mapped[int] = mapped_column(Integer)
    condition_codes: Mapped[list] = mapped_column(JSON)
    source_url: Mapped[str] = mapped_column(String(500))
    note: Mapped[str] = mapped_column(String(500))
    synced_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class PurineReference(Base):
    __tablename__ = "purine_references"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    food_name_en: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(50))
    total_purines_mg: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))
    sample_n: Mapped[str] = mapped_column(String(100))
    year: Mapped[str] = mapped_column(String(100))
    source_code: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(500))
    synced_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class FoodCompositionReference(Base):
    __tablename__ = "food_composition_references"
    fdc_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description_en: Mapped[str] = mapped_column(String(700), index=True)
    data_type: Mapped[str] = mapped_column(String(40), index=True)
    release: Mapped[str] = mapped_column(String(20))
    energy_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbohydrate_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sodium_mg: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str] = mapped_column(String(500))
    synced_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class HealthTopicReference(Base):
    __tablename__ = "health_topic_references"
    topic_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title_en: Mapped[str] = mapped_column(String(300), index=True)
    title_zh: Mapped[str | None] = mapped_column(String(150), nullable=True)
    summary_en: Mapped[str] = mapped_column(String(3000))
    condition_codes: Mapped[list] = mapped_column(JSON)
    source_url: Mapped[str] = mapped_column(String(500))
    release: Mapped[str] = mapped_column(String(20))
    synced_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
