"""루트 스키마"""
from pydantic import BaseModel, Field


class RouteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    sequence: int = Field(default=0, ge=0)


class RouteCreate(RouteBase):
    pass


class RouteUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    sequence: int | None = Field(None, ge=0)


class RouteAssignmentCreate(BaseModel):
    driver_id: int


class RouteAssignmentSet(BaseModel):
    """기사 배정 설정 (driver_id 없으면 배정 해제)"""
    driver_id: int | None = None


class RouteResponse(RouteBase):
    id: int
    plan_id: int

    model_config = {"from_attributes": True}
