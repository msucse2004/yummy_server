"""앱 설정 API - ADMIN 전용"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.auth import require_user, require_role
from app.database import get_db
from app.models import User, AppSetting
from app.models.user import Role
from app.services.geocode import geocode_address

router = APIRouter(prefix="/api/settings", tags=["settings"])
RequireAdmin = Depends(require_role(Role.ADMIN))

COMPANY_NAME_KEY = "company_name"
COMPANY_ADDRESS_KEY = "company_address"
COMPANY_PHONE_KEY = "company_phone"
DELIVERY_ROUTE_COUNT_KEY = "delivery_route_count"
BUSINESS_REGISTRATION_NUMBER_KEY = "business_registration_number"
REPRESENTATIVE_NAME_KEY = "representative_name"
BUSINESS_TYPE_KEY = "business_type"
BUSINESS_CATEGORY_KEY = "business_category"
BANK_NAME_KEY = "bank_name"
BANK_ACCOUNT_KEY = "bank_account"
BANK_HOLDER_KEY = "bank_holder"


class SettingsResponse(BaseModel):
    company_name: str = ""
    company_address: str = ""
    company_phone: str = ""
    delivery_route_count: int = 5
    business_registration_number: str = ""
    representative_name: str = ""
    business_type: str = ""
    business_category: str = ""
    bank_name: str = ""
    bank_account: str = ""
    bank_holder: str = ""


class SettingsUpdate(BaseModel):
    company_name: str | None = Field(None, max_length=128)
    company_address: str | None = Field(None, max_length=256)
    company_phone: str | None = Field(None, max_length=32)
    delivery_route_count: int | None = Field(None, ge=1, le=99)
    business_registration_number: str | None = Field(None, max_length=32)
    representative_name: str | None = Field(None, max_length=64)
    business_type: str | None = Field(None, max_length=64)
    business_category: str | None = Field(None, max_length=64)
    bank_name: str | None = Field(None, max_length=64)
    bank_account: str | None = Field(None, max_length=64)
    bank_holder: str | None = Field(None, max_length=64)


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


@router.get("/geocode")
def geocode_address_api(
    address: str = Query(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """주소를 지오코딩 (실시간 검증용)"""
    if not address or not address.strip():
        return {"latitude": None, "longitude": None, "found": False}
    settings = get_settings()
    lat, lon = geocode_address(address.strip(), settings.kakao_rest_api_key or "")
    return {
        "latitude": float(lat) if lat is not None else None,
        "longitude": float(lon) if lon is not None else None,
        "found": lat is not None and lon is not None,
    }


@router.get("/company-location")
def get_company_location(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """회사 주소를 지오코딩하여 위도/경도 반환 (맵 출발지용)"""
    addr = _get_str_setting(db, COMPANY_ADDRESS_KEY)
    if not addr or not addr.strip():
        return {"latitude": None, "longitude": None}
    settings = get_settings()
    lat, lon = geocode_address(addr.strip(), settings.kakao_rest_api_key or "")
    return {"latitude": float(lat) if lat is not None else None, "longitude": float(lon) if lon is not None else None}


@router.get("", response_model=SettingsResponse)
def get_settings_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """설정 조회 (GET /api/settings - get_settings와 이름 충돌 방지를 위해 get_settings_api 사용)"""
    return SettingsResponse(
        company_name=_get_str_setting(db, COMPANY_NAME_KEY),
        company_address=_get_str_setting(db, COMPANY_ADDRESS_KEY),
        company_phone=_get_str_setting(db, COMPANY_PHONE_KEY),
        delivery_route_count=_get_int_setting(db, DELIVERY_ROUTE_COUNT_KEY, 5),
        business_registration_number=_get_str_setting(db, BUSINESS_REGISTRATION_NUMBER_KEY),
        representative_name=_get_str_setting(db, REPRESENTATIVE_NAME_KEY),
        business_type=_get_str_setting(db, BUSINESS_TYPE_KEY),
        business_category=_get_str_setting(db, BUSINESS_CATEGORY_KEY),
        bank_name=_get_str_setting(db, BANK_NAME_KEY),
        bank_account=_get_str_setting(db, BANK_ACCOUNT_KEY),
        bank_holder=_get_str_setting(db, BANK_HOLDER_KEY),
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
        elif k == "business_registration_number":
            _set_setting(db, BUSINESS_REGISTRATION_NUMBER_KEY, v or "")
        elif k == "representative_name":
            _set_setting(db, REPRESENTATIVE_NAME_KEY, v or "")
        elif k == "business_type":
            _set_setting(db, BUSINESS_TYPE_KEY, v or "")
        elif k == "business_category":
            _set_setting(db, BUSINESS_CATEGORY_KEY, v or "")
        elif k == "bank_name":
            _set_setting(db, BANK_NAME_KEY, v or "")
        elif k == "bank_account":
            _set_setting(db, BANK_ACCOUNT_KEY, v or "")
        elif k == "bank_holder":
            _set_setting(db, BANK_HOLDER_KEY, v or "")
    db.commit()
    return SettingsResponse(
        company_name=_get_str_setting(db, COMPANY_NAME_KEY),
        company_address=_get_str_setting(db, COMPANY_ADDRESS_KEY),
        company_phone=_get_str_setting(db, COMPANY_PHONE_KEY),
        delivery_route_count=_get_int_setting(db, DELIVERY_ROUTE_COUNT_KEY, 5),
        business_registration_number=_get_str_setting(db, BUSINESS_REGISTRATION_NUMBER_KEY),
        representative_name=_get_str_setting(db, REPRESENTATIVE_NAME_KEY),
        business_type=_get_str_setting(db, BUSINESS_TYPE_KEY),
        business_category=_get_str_setting(db, BUSINESS_CATEGORY_KEY),
        bank_name=_get_str_setting(db, BANK_NAME_KEY),
        bank_account=_get_str_setting(db, BANK_ACCOUNT_KEY),
        bank_holder=_get_str_setting(db, BANK_HOLDER_KEY),
    )
