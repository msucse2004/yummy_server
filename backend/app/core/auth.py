"""세션 기반 인증 - HttpOnly 쿠키, DB 세션"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import generate_session_id, verify_password, hash_password
from app.database import get_db
from app.models import User, DbSession
from app.models.user import Role

settings = get_settings()


def _get_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=settings.session_max_age_seconds)


def create_session(db: Session, user: User) -> str:
    """세션 생성, session_id 반환"""
    session_id = generate_session_id()
    db_session = DbSession(
        session_id=session_id,
        user_id=user.id,
        expires_at=_get_expires_at(),
    )
    db.add(db_session)
    db.commit()
    return session_id


def get_user_from_session(
    db: Annotated[Session, Depends(get_db)],
    response: Response,
    yummy_session: Annotated[str | None, Cookie()] = None,
) -> User | None:
    """쿠키의 세션 ID로 사용자 조회. 없거나 만료 시 None."""
    if not yummy_session:
        return None
    stmt = (
        select(DbSession)
        .join(User)
        .where(DbSession.session_id == yummy_session)
        .where(DbSession.expires_at > datetime.now(timezone.utc))
    )
    row = db.execute(stmt).scalar_one_or_none()
    if not row:
        # 세션 무효화 - 쿠키 삭제
        response.delete_cookie(settings.session_cookie_name)
        return None
    return row.user


def require_user(
    user: Annotated[User | None, Depends(get_user_from_session)],
) -> User:
    """인증 필수 - 로그인 필요"""
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다")
    return user


def require_role(role: Role):
    """역할 기반 접근 - 지정 역할만 허용"""

    def _check(current_user: Annotated[User, Depends(require_user)]) -> User:
        if current_user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다")
        return current_user

    return _check


RequireAdmin = Depends(require_role(Role.ADMIN))
RequireDriver = Depends(require_role(Role.DRIVER))


def set_session_cookie(response: Response, session_id: str) -> None:
    """HttpOnly + Secure + SameSite=Lax 쿠키 설정"""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        domain=settings.cookie_domain if settings.cookie_domain != "localhost" else None,
    )


def clear_session_cookie(response: Response) -> None:
    """세션 쿠키 삭제"""
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
    )
