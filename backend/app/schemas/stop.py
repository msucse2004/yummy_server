"""스탑 스키마"""
from decimal import Decimal
from pydantic import BaseModel, Field


class StopOrderItemBase(BaseModel):
    item_id: int
    quantity: Decimal = Field(default=1, gt=0)
    memo: str | None = None


class StopOrderItemCreate(StopOrderItemBase):
    pass


class StopBase(BaseModel):
    customer_id: int
    sequence: int = Field(default=0, ge=0)
    memo: str | None = None


class StopCreate(StopBase):
    order_items: list[StopOrderItemCreate] = Field(default_factory=list)


class StopUpdate(BaseModel):
    customer_id: int | None = None
    sequence: int | None = Field(None, ge=0)
    memo: str | None = None


class StopOrderItemResponse(StopOrderItemBase):
    id: int
    stop_id: int

    model_config = {"from_attributes": True}


class StopResponse(StopBase):
    id: int
    route_id: int
    order_items: list[StopOrderItemResponse] = Field(default_factory=list)
    is_completed: bool = False

    model_config = {"from_attributes": True}
