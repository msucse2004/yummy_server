"""루트 CRUD - ADMIN 관리, DRIVER는 배정된 루트만"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.auth import require_user, require_role
from app.core.route_access import require_route_access
from app.database import get_db
from app.models import User, Route, Plan, RouteAssignment
from app.models.user import Role
from app.schemas.route import RouteCreate, RouteUpdate, RouteResponse, RouteAssignmentCreate, RouteAssignmentSet

router = APIRouter(prefix="/api/routes", tags=["routes"])
RequireAdmin = Depends(require_role(Role.ADMIN))


def _get_route_with_assignments(db: Session, route_id: int) -> Route | None:
    return db.get(Route, route_id, options=[joinedload(Route.assignments)])


@router.get("/plan/{plan_id}", response_model=list[RouteResponse])
def list_routes_by_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="플랜을 찾을 수 없습니다")
    if current_user.role == Role.DRIVER:
        # 배정된 루트만
        routes = [r for r in plan.routes if any(a.driver_id == current_user.id for a in r.assignments)]
    else:
        routes = plan.routes
    return sorted(routes, key=lambda r: (r.sequence, r.id))


@router.post("/plan/{plan_id}", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
def create_route(
    plan_id: int,
    data: RouteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="플랜을 찾을 수 없습니다")
    route = Route(plan_id=plan_id, **data.model_dump())
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


@router.get("/{route_id}", response_model=RouteResponse)
def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    route = _get_route_with_assignments(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="루트를 찾을 수 없습니다")
    require_route_access(current_user, route)
    return route


@router.patch("/{route_id}", response_model=RouteResponse)
def update_route(
    route_id: int,
    data: RouteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    route = db.get(Route, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="루트를 찾을 수 없습니다")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(route, k, v)
    db.commit()
    db.refresh(route)
    return route


@router.post("/{route_id}/assign", status_code=status.HTTP_204_NO_CONTENT)
def assign_driver(
    route_id: int,
    data: RouteAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    route = _get_route_with_assignments(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="루트를 찾을 수 없습니다")
    existing = next((a for a in route.assignments if a.driver_id == data.driver_id), None)
    if existing:
        return
    assignment = RouteAssignment(route_id=route_id, driver_id=data.driver_id)
    db.add(assignment)
    db.commit()


@router.put("/{route_id}/assign", status_code=status.HTTP_204_NO_CONTENT)
def set_route_driver(
    route_id: int,
    data: RouteAssignmentSet,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """기사 배정 설정 (기존 배정 제거 후 새로 배정, driver_id 없으면 배정 해제)"""
    from sqlalchemy import delete
    route = _get_route_with_assignments(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="루트를 찾을 수 없습니다")
    db.execute(delete(RouteAssignment).where(RouteAssignment.route_id == route_id))
    if data and data.driver_id:
        db.add(RouteAssignment(route_id=route_id, driver_id=data.driver_id))
    db.commit()


@router.post("/{route_id}/start", status_code=status.HTTP_204_NO_CONTENT)
def start_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """배송 시작 - 배정된 기사만 호출 가능. routes.started_at 갱신."""
    route = _get_route_with_assignments(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="루트를 찾을 수 없습니다")
    require_route_access(current_user, route)
    route.started_at = datetime.now(timezone.utc)
    db.commit()


@router.delete("/{route_id}/assign/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_driver(
    route_id: int,
    driver_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    from sqlalchemy import delete
    db.execute(delete(RouteAssignment).where(
        RouteAssignment.route_id == route_id,
        RouteAssignment.driver_id == driver_id,
    ))
    db.commit()


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    route = db.get(Route, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="루트를 찾을 수 없습니다")
    db.delete(route)
    db.commit()
