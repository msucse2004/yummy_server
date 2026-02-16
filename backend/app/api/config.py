"""클라이언트용 설정 API - 인증된 사용자만 접근"""
from fastapi import APIRouter, Depends

from app.config import get_settings
from app.core.auth import require_user
from app.models import User

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/client")
def get_client_config(current_user: User = Depends(require_user)):
    """드라이버 앱 등에서 사용할 클라이언트 설정 (카카오맵 JS 키 등)"""
    settings = get_settings()
    return {
        "kakao_map_js_key": settings.kakao_javascript_key or "",
    }
