"""인증 API - 로그인/로그아웃"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import (
    create_session,
    set_session_cookie,
    clear_session_cookie,
    get_user_from_session,
    require_user,
)
from app.core.security import verify_password
from app.database import get_db
from app.models import User
from app.schemas.auth import LoginRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """로그인 - 성공 시 HttpOnly 쿠키 설정"""
    stmt = select(User).where(User.username == data.username)
    user = db.execute(stmt).scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="아이디 또는 비밀번호가 잘못되었습니다")
    session_id = create_session(db, user)
    set_session_cookie(response, session_id)
    return {"ok": True, "user": UserResponse.model_validate(user)}


@router.post("/logout")
def logout(response: Response, db: Session = Depends(get_db)):
    """로그아웃 - 쿠키 삭제 (세션 DB 레코드는 만료 시 정리)"""
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(require_user)):
    """현재 로그인 사용자 정보"""
    return current_user
