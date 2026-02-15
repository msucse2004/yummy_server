"""앱 설정 API - ADMIN 전용"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_user, require_role
from app.database import get_db
from app.models import User, AppSetting
from app.models.user import Role

router = APIRouter(prefix="/api/settings", tags=["settings"])
RequireAdmin = Depends(require_role(Role.ADMIN))

COMPANY_NAME_KEY = "company_name"
COMPANY_ADDRESS_KEY = "company_address"
COMPANY_PHONE_KEY = "company_phone"
DELIVERY_ROUTE_COUNT_KEY = "delivery_route_count"


class SettingsResponse(BaseModel):
    company_name: str = ""
    company_address: str = ""
    company_phone: str = ""
    delivery_route_count: int = 5


class SettingsUpdate(BaseModel):
    company_name: str | None = Field(None, max_length=128)
    company_address: str | None = Field(None, max_length=256)
    company_phone: str | None = Field(None, max_length=32)
    delivery_route_count: int | None = Field(None, ge=1, le=99)


def _get_str_setting(db: Session, key: str, default: str = "") -> str:
    row = db.execute(select(AppSetting).where(AppSetting.key == key)).scalars().first()
    return row.value if row else default


def _get_int_setting(db: Session, key: str, default: int) -> int:
    row = db.execute(select(AppSetting).where(AppSetting.key == key)).scalars().first()
    if not row:
        return default
    try:
        return int(row.value)
    except (ValueError, TypeError):
        return default


def _set_setting(db: Session, key: str, value: str) -> None:
    row = db.execute(select(AppSetting).where(AppSetting.key == key)).scalars().first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))


@router.get("", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """설정 조회"""
    return SettingsResponse(
        company_name=_get_str_setting(db, COMPANY_NAME_KEY),
        company_address=_get_str_setting(db, COMPANY_ADDRESS_KEY),
        company_phone=_get_str_setting(db, COMPANY_PHONE_KEY),
        delivery_route_count=_get_int_setting(db, DELIVERY_ROUTE_COUNT_KEY, 5),
    )


@router.patch("", response_model=SettingsResponse)
def update_settings(
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """설정 수정"""
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == "delivery_route_count":
            _set_setting(db, DELIVERY_ROUTE_COUNT_KEY, str(v))
        elif k == "company_name":
            _set_setting(db, COMPANY_NAME_KEY, v or "")
        elif k == "company_address":
            _set_setting(db, COMPANY_ADDRESS_KEY, v or "")
        elif k == "company_phone":
            _set_setting(db, COMPANY_PHONE_KEY, v or "")
    db.commit()
    return SettingsResponse(
        company_name=_get_str_setting(db, COMPANY_NAME_KEY),
        company_address=_get_str_setting(db, COMPANY_ADDRESS_KEY),
        company_phone=_get_str_setting(db, COMPANY_PHONE_KEY),
        delivery_route_count=_get_int_setting(db, DELIVERY_ROUTE_COUNT_KEY, 5),
    )
