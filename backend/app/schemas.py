from datetime import date, datetime
from typing import Annotated, Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

ShortText = Annotated[str, Field(min_length=1, max_length=100)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PatientCreate(InputModel):
    name: ShortText
    age: int = Field(ge=0, le=130)
    sex: Literal["female", "male", "other", "unspecified"] = "unspecified"
    height_cm: float = Field(gt=0, le=300, allow_inf_nan=False)
    weight_kg: float = Field(gt=0, le=700, allow_inf_nan=False)
    allergies: list[ShortText] = Field(default_factory=list, max_length=100)
    dietary_preferences: list[ShortText] = Field(default_factory=list, max_length=100)


class PatientRead(PatientCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    bmi: float
    created_at: datetime


class ConditionCreate(InputModel):
    disease_code: ShortText
    status: Literal["active", "resolved", "inactive"] = "active"
    diagnosis_date: date | None = None
    severity: Literal["unspecified", "mild", "moderate", "severe"] = "unspecified"
    notes: str = Field(default="", max_length=2000)


class ConditionRead(ConditionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    disease_name: str


ClockTime = Annotated[str, Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")]


class MedicationCreate(InputModel):
    drug_name: ShortText
    generic_name: ShortText
    dose: float = Field(gt=0, allow_inf_nan=False)
    unit: Annotated[str, Field(min_length=1, max_length=30)]
    route: Literal["oral", "injection", "topical", "inhalation", "other"] = "oral"
    frequency: Literal["once_daily", "twice_daily", "three_times_daily", "daily"] = "once_daily"
    administration_time: list[ClockTime] = Field(min_length=1, max_length=12)
    meal_relation: Literal["before_meal", "with_meal", "after_meal", "fasting", "anytime"] = "anytime"
    start_date: date
    end_date: date | None = None
    indication: str = Field(default="", max_length=500)
    active: bool = True

    @model_validator(mode="after")
    def valid_schedule(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        if len(set(self.administration_time)) != len(self.administration_time):
            raise ValueError("administration_time must not contain duplicate times")
        count = {"once_daily": 1, "twice_daily": 2, "three_times_daily": 3}.get(self.frequency)
        if count and len(self.administration_time) != count:
            raise ValueError("frequency and administration_time count do not agree")
        self.administration_time = sorted(self.administration_time)
        self.generic_name = self.generic_name.casefold()
        return self


class MedicationRead(MedicationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int


class MedicationEventCreate(InputModel):
    scheduled_date: date
    scheduled_time: ClockTime
    status: Literal["taken", "missed", "delayed"]
    taken_at: AwareDatetime | None = None
    delayed_to: ClockTime | None = None
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def valid_status(self):
        if self.status == "taken" and self.taken_at is None:
            raise ValueError("taken status requires taken_at including timezone")
        if self.status != "taken" and self.taken_at is not None:
            raise ValueError("taken_at is only valid for taken status")
        if self.status == "delayed" and (self.delayed_to is None or self.delayed_to <= self.scheduled_time):
            raise ValueError("delayed_to must be later on the same day")
        if self.status != "delayed" and self.delayed_to is not None:
            raise ValueError("delayed_to is only valid for delayed status")
        return self


class MedicationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    medication_id: int
    scheduled_date: date
    scheduled_time: str
    status: str
    taken_at: datetime | None
    delayed_to: str | None
    notes: str
    medication_snapshot: dict
    recorded_at: datetime


METRIC_UNITS = {
    "blood_pressure": "mmHg", "fasting_glucose": "mmol/L", "postprandial_glucose": "mmol/L",
    "HbA1c": "%", "heart_rate": "bpm", "body_weight": "kg", "uric_acid": "umol/L",
    "cholesterol": "mmol/L", "triglycerides": "mmol/L", "LDL": "mmol/L", "HDL": "mmol/L",
    "creatinine": "umol/L", "eGFR": "mL/min/1.73m2",
}
MetricType = Literal["blood_pressure", "fasting_glucose", "postprandial_glucose", "HbA1c", "heart_rate", "body_weight", "uric_acid", "cholesterol", "triglycerides", "LDL", "HDL", "creatinine", "eGFR"]


class ObservationCreate(InputModel):
    metric_type: MetricType
    value: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    systolic: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    diastolic: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    unit: str = Field(max_length=30)
    measured_at: AwareDatetime
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_measurement(self):
        if self.unit != METRIC_UNITS[self.metric_type]:
            raise ValueError(f"Expected unit: {METRIC_UNITS[self.metric_type]}")
        if self.metric_type == "blood_pressure":
            if self.value is not None or self.systolic is None or self.diastolic is None or self.systolic <= self.diastolic:
                raise ValueError("Blood pressure requires systolic > diastolic; do not use value")
        elif self.value is None or self.systolic is not None or self.diastolic is not None:
            raise ValueError("This metric requires value only")
        return self


class ObservationRead(ObservationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
