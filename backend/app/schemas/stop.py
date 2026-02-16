"""스탑 스키마"""
from decimal import Decimal
from pydantic import BaseModel, Field


class ItemSummary(BaseModel):
    """품목 요약 - 스탑 주문 품목 표시용"""
    id: int
    code: str
    product: str
    unit: str = "박스"

    model_config = {"from_attributes": True}


class StopOrderItemBase(BaseModel):
    item_id: int
    quantity: Decimal = Field(default=1, gt=0)
    memo: str | None = None


class StopOrderItemCreate(StopOrderItemBase):
    pass


class CustomerSummary(BaseModel):
    id: int
    name: str
    address: str | None = None
    phone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    model_config = {"from_attributes": True}


class PhotoSummary(BaseModel):
    id: int
    model_config = {"from_attributes": True}


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
    item: ItemSummary | None = None

    model_config = {"from_attributes": True}


class CompletionPhotoSummary(BaseModel):
    id: int
    model_config = {"from_attributes": True}


class CompletionSummary(BaseModel):
    id: int
    photos: list[PhotoSummary] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class StopResponse(StopBase):
    id: int
    route_id: int
    order_items: list[StopOrderItemResponse] = Field(default_factory=list)
    is_completed: bool = False
    customer: CustomerSummary | None = None
    completions: list[CompletionSummary] = Field(default_factory=list)

    model_config = {"from_attributes": True}
