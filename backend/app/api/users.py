"""사용자 관리 - ADMIN 전용 (기사 생성 등)"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_user, require_role
from app.core.security import hash_password
from app.database import get_db
from app.models import User
from app.models.user import Role
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])
RequireAdmin = Depends(require_role(Role.ADMIN))


class UserCreateSchema(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6)
    role: Role = Role.DRIVER
    display_name: str | None = Field(None, max_length=128)


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    stmt = select(User).order_by(User.id)
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    existing = db.execute(select(User).where(User.username == data.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="사용자명이 이미 존재합니다")
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role,
        display_name=data.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
