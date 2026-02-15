"""거래처 스키마"""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

ContractType = Literal["계약", "해지"]


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: str | None = Field(None, max_length=64)
    route: str | None = Field(None, max_length=64)
    business_registration_number: str | None = Field(None, max_length=32)
    representative_name: str | None = Field(None, max_length=64)
    phone: str | None = Field(None, max_length=32)
    contract: ContractType | None = None
    business_type: str | None = Field(None, max_length=64)
    business_category: str | None = Field(None, max_length=64)
    arrears: Decimal | float | None = Field(None, description="미수금액")
    contract_content: str | None = Field(None, max_length=1024)
    address: str | None = None
    latitude: Decimal | float | None = None
    longitude: Decimal | float | None = None
    memo: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    code: str | None = Field(None, max_length=64)
    route: str | None = Field(None, max_length=64)
    business_registration_number: str | None = Field(None, max_length=32)
    representative_name: str | None = Field(None, max_length=64)
    address: str | None = None
    phone: str | None = Field(None, max_length=32)
    contract: ContractType | None = None
    business_type: str | None = Field(None, max_length=64)
    business_category: str | None = Field(None, max_length=64)
    arrears: Decimal | float | None = Field(None, description="미수금액")
    contract_content: str | None = Field(None, max_length=1024)
    latitude: Decimal | float | None = None
    longitude: Decimal | float | None = None
    memo: str | None = None


class CustomerResponse(CustomerBase):
    id: int

    model_config = {"from_attributes": True}
