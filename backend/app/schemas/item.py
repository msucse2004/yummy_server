"""품목 스키마 - 코드는 API에서 자동 생성, 단가는 원화(정수), 단위는 박스/판/관"""
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

UNIT_CHOICES = ("박스", "판", "관")


def _round_unit_price(v):
    """단가(원)는 소수점 없이 정수로 저장"""
    if v is None:
        return None
    return Decimal(int(v))


def _normalize_unit(v):
    """단위: 박스, 판, 관만 허용"""
    if v is None or (isinstance(v, str) and not v.strip()):
        return "박스"
    s = str(v).strip()
    return s if s in UNIT_CHOICES else "박스"


class ItemBase(BaseModel):
    product: str = Field(..., min_length=1, max_length=128)  # 상품
    weight: Decimal | None = None  # 무게
    unit: str = Field(default="박스", max_length=32)  # 단위: 박스, 판, 관
    unit_price: Decimal | None = None  # 단가 (원, 정수)
    description: str | None = Field(None, max_length=256)  # 설명

    @field_validator("unit_price", mode="before")
    @classmethod
    def round_unit_price(cls, v):
        return _round_unit_price(v)

    @field_validator("unit", mode="before")
    @classmethod
    def normalize_unit(cls, v):
        return _normalize_unit(v)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    product: str | None = Field(None, min_length=1, max_length=128)
    weight: Decimal | None = None
    unit: str | None = Field(None, max_length=32)
    unit_price: Decimal | None = None
    description: str | None = Field(None, max_length=256)

    @field_validator("unit_price", mode="before")
    @classmethod
    def round_unit_price(cls, v):
        return _round_unit_price(v)

    @field_validator("unit", mode="before")
    @classmethod
    def normalize_unit(cls, v):
        return _normalize_unit(v)


class ItemResponse(ItemBase):
    id: int
    code: str

    model_config = {"from_attributes": True}
