"""거래처 스키마"""
from typing import Literal

from pydantic import BaseModel, Field

ContractType = Literal["계약", "해지"]


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: str | None = Field(None, max_length=64)
    route: str | None = Field(None, max_length=64)
    address: str | None = None
    phone: str | None = Field(None, max_length=32)
    contract: ContractType | None = None
    memo: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    code: str | None = Field(None, max_length=64)
    route: str | None = Field(None, max_length=64)
    address: str | None = None
    phone: str | None = Field(None, max_length=32)
    contract: ContractType | None = None
    memo: str | None = None


class CustomerResponse(CustomerBase):
    id: int

    model_config = {"from_attributes": True}
