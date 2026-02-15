"""품목 스키마 - 코드는 API에서 자동 생성"""
from decimal import Decimal

from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    product: str = Field(..., min_length=1, max_length=128)  # 상품
    weight: Decimal | None = None  # 무게
    unit: str = Field(default="EA", max_length=32)  # 단위
    unit_price: Decimal | None = None  # 단가


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    product: str | None = Field(None, min_length=1, max_length=128)
    weight: Decimal | None = None
    unit: str | None = Field(None, max_length=32)
    unit_price: Decimal | None = None


class ItemResponse(ItemBase):
    id: int
    code: str

    model_config = {"from_attributes": True}
