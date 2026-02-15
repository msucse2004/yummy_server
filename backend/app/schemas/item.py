"""품목 스키마"""
from decimal import Decimal
from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: str | None = Field(None, max_length=64)
    unit: str = Field(default="EA", max_length=32)
    price: Decimal | None = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    code: str | None = Field(None, max_length=64)
    unit: str | None = Field(None, max_length=32)
    price: Decimal | None = None


class ItemResponse(ItemBase):
    id: int

    model_config = {"from_attributes": True}
