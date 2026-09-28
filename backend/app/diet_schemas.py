from datetime import date
from typing import Literal
from pydantic import Field, model_validator
from .schemas import InputModel, PatientCreate, MedicationCreate, ShortText
from core.disease.engine import catalog
from core.nutrition.scoring import diet_catalog
from core.activity.engine import exercise_catalog


class IntakeMedication(MedicationCreate):
    id: int | None = Field(default=None, gt=0)


class Intake(InputModel):
    patient: PatientCreate
    conditions: list[ShortText] = Field(default_factory=list, max_length=20)
    medications: list[IntakeMedication] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def valid_conditions(self):
        if len(set(self.conditions)) != len(self.conditions):
            raise ValueError("请勿重复选择疾病")
        if set(self.conditions) - set(catalog()):
            raise ValueError("存在当前不支持的疾病编码")
        ids = [m.id for m in self.medications if m.id is not None]
        if len(set(ids)) != len(ids):
            raise ValueError("药物记录 ID 不可重复")
        return self


class FoodEntry(InputModel):
    food_id: ShortText
    servings: float = Field(gt=0, le=20, allow_inf_nan=False)
    description: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def known_food(self):
        if self.food_id not in {f["id"] for f in diet_catalog()["foods"]}:
            raise ValueError("未知食物编码，请选择其他食物并填写名称")
        if self.food_id == "other" and not self.description:
            raise ValueError("其他食物需要填写名称与份量")
        return self


class Meal(InputModel):
    name: Literal["breakfast", "lunch", "dinner", "snack"]
    status: Literal["recorded", "skipped", "unreported"] = "unreported"
    items: list[FoodEntry] = Field(default_factory=list, max_length=30)
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def consistent(self):
        if self.status == "recorded" and not self.items:
            raise ValueError("已记录的餐次至少需要一种食物")
        if self.status != "recorded" and self.items:
            raise ValueError("有食物记录时请选择已记录")
        return self


class DietDay(InputModel):
    day: date
    day_complete: bool = False
    activity_level: Literal["inactive", "light_active", "low_active", "active", "very_active"] | None = None
    exercise_activity_id: ShortText | None = None
    exercise_minutes: int = Field(default=0, ge=0, le=300)
    meals: list[Meal] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def all_meals(self):
        if {m.name for m in self.meals} != {"breakfast", "lunch", "dinner", "snack"}:
            raise ValueError("需要早餐、午餐、晚餐和加餐各一条")
        known = {activity["id"] for activity in exercise_catalog()["activities"]}
        if self.exercise_activity_id is not None and self.exercise_activity_id not in known:
            raise ValueError("未知运动项目")
        if bool(self.exercise_activity_id) != bool(self.exercise_minutes):
            raise ValueError("运动项目与实际时长需要同时填写")
        return self
