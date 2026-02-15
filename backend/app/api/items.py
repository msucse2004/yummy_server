"""품목 CRUD - ADMIN 전용"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_user, require_role
from app.database import get_db
from app.models import User, Item
from app.models.user import Role
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse

router = APIRouter(prefix="/api/items", tags=["items"])
RequireAdmin = Depends(require_role(Role.ADMIN))


@router.get("", response_model=list[ItemResponse])
def list_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    stmt = select(Item).order_by(Item.name)
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    data: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    if data.code:
        existing = db.execute(select(Item).where(Item.code == data.code)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="품목 코드가 이미 존재합니다")
    item = Item(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="품목을 찾을 수 없습니다")
    return item


@router.patch("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int,
    data: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="품목을 찾을 수 없습니다")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    if data.code is not None and data.code != "":
        existing = db.execute(
            select(Item).where(Item.code == data.code, Item.id != item_id)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="품목 코드가 이미 존재합니다")
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="품목을 찾을 수 없습니다")
    db.delete(item)
    db.commit()
