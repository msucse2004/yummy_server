"""플랜 스키마"""
from datetime import date
from pydantic import BaseModel, Field


class PlanBase(BaseModel):
    plan_date: date
    route: str | None = Field(None, max_length=32)
    name: str = Field(..., min_length=1, max_length=128)
    memo: str | None = Field(None, max_length=512)


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    plan_date: date | None = None
    route: str | None = Field(None, max_length=32)
    name: str | None = Field(None, min_length=1, max_length=128)
    memo: str | None = Field(None, max_length=512)


class PlanResponse(PlanBase):
    id: int

    model_config = {"from_attributes": True}
