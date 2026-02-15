"""스탑 CRUD - ADMIN 관리, DRIVER는 배정된 루트의 스탑만"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.auth import require_user, require_role
from app.core.route_access import require_route_access
from app.database import get_db
from app.models import User, Route, Stop, StopOrderItem, Customer, Item
from app.models.user import Role
from app.schemas.stop import StopCreate, StopUpdate, StopResponse, StopOrderItemResponse

router = APIRouter(prefix="/api/stops", tags=["stops"])
RequireAdmin = Depends(require_role(Role.ADMIN))


def _get_route_with_assignments(db: Session, route_id: int) -> Route | None:
    return db.get(Route, route_id, options=[joinedload(Route.assignments)])


def _get_stop_with_route(db: Session, stop_id: int) -> Stop | None:
    return db.get(
        Stop,
        stop_id,
        options=[
            joinedload(Stop.route).joinedload(Route.assignments),
            joinedload(Stop.order_items).joinedload(StopOrderItem.item),
            joinedload(Stop.customer),
        ],
    )


@router.get("/route/{route_id}", response_model=list[StopResponse])
def list_stops_by_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    route = _get_route_with_assignments(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="루트를 찾을 수 없습니다")
    require_route_access(current_user, route)
    stmt = (
        select(Stop)
        .where(Stop.route_id == route_id)
        .order_by(Stop.sequence, Stop.id)
        .options(
            joinedload(Stop.order_items).joinedload(StopOrderItem.item),
            joinedload(Stop.customer),
            joinedload(Stop.completions),
        )
    )
    return list(db.execute(stmt).scalars().unique().all())


@router.post("/route/{route_id}", response_model=StopResponse, status_code=status.HTTP_201_CREATED)
def create_stop(
    route_id: int,
    data: StopCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    route = _get_route_with_assignments(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="루트를 찾을 수 없습니다")
    if not db.get(Customer, data.customer_id):
        raise HTTPException(status_code=404, detail="거래처를 찾을 수 없습니다")
    stop = Stop(route_id=route_id, customer_id=data.customer_id, sequence=data.sequence, memo=data.memo)
    db.add(stop)
    db.flush()
    for oi in data.order_items:
        if not db.get(Item, oi.item_id):
            raise HTTPException(status_code=404, detail=f"품목 ID {oi.item_id}를 찾을 수 없습니다")
        db.add(StopOrderItem(stop_id=stop.id, item_id=oi.item_id, quantity=oi.quantity, memo=oi.memo))
    db.commit()
    db.refresh(stop)
    return stop


@router.get("/{stop_id}", response_model=StopResponse)
def get_stop(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    stop = _get_stop_with_route(db, stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail="스탑을 찾을 수 없습니다")
    require_route_access(current_user, stop.route)
    return stop


@router.patch("/{stop_id}", response_model=StopResponse)
def update_stop(
    stop_id: int,
    data: StopUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    stop = _get_stop_with_route(db, stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail="스탑을 찾을 수 없습니다")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(stop, k, v)
    db.commit()
    db.refresh(stop)
    return stop


@router.delete("/{stop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stop(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    stop = db.get(Stop, stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail="스탑을 찾을 수 없습니다")
    db.delete(stop)
    db.commit()
