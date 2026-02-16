"""인증 API - 로그인/로그아웃/회원가입"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import (
    create_session,
    set_session_cookie,
    clear_session_cookie,
    require_user,
)
from app.core.security import hash_password, verify_password
from app.database import get_db
from app.models import User
from app.models.user import Role
from app.schemas.auth import ChangePasswordRequest, LoginRequest, SignupRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/check-username")
def check_username(
    username: str,
    db: Session = Depends(get_db),
):
    """아이디 중복 확인 - 비인증 접근 가능"""
    username = (username or "").strip()
    if not username:
        return {"available": False}
    existing = db.execute(select(User).where(User.username == username)).scalars().first()
    return {"available": existing is None}


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    data: SignupRequest,
    db: Session = Depends(get_db),
):
    """회원가입 - 비인증 접근 가능, role=DRIVER, status=승인요청중"""
    existing = db.execute(select(User).where(User.username == data.username)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 사용 중인 아이디입니다")
    preferred_locale = (data.preferred_locale or "").strip() or "대한민국"
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=Role.DRIVER,
        display_name=data.display_name,
        phone=data.phone,
        status="승인요청중",
        preferred_locale=preferred_locale,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """로그인 사용자가 본인 비밀번호 변경 (임시 비밀번호 사용 시 필수)"""
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다")
    current_user.password_hash = hash_password(data.new_password)
    current_user.must_change_password = False
    db.commit()
