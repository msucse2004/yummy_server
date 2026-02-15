"""플랜 CRUD - ADMIN 생성/수정, DRIVER는 배정된 플랜만 조회"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.auth import require_user, require_role
from app.database import get_db
from app.models import User, Plan, Route, RouteAssignment
from app.models.user import Role
from app.schemas.plan import PlanCreate, PlanUpdate, PlanResponse

router = APIRouter(prefix="/api/plans", tags=["plans"])
RequireAdmin = Depends(require_role(Role.ADMIN))


@router.get("", response_model=list[PlanResponse])
def list_plans(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    stmt = select(Plan).order_by(Plan.plan_date.desc(), Plan.id.desc())
    if from_date:
        stmt = stmt.where(Plan.plan_date >= from_date)
    if to_date:
        stmt = stmt.where(Plan.plan_date <= to_date)
    if current_user.role == Role.DRIVER:
        stmt = stmt.join(Plan.routes).join(Route.assignments).where(
            RouteAssignment.driver_id == current_user.id
        )
    return list(db.execute(stmt).scalars().unique().all())


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    data: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    plan = Plan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="플랜을 찾을 수 없습니다")
    if current_user.role == Role.DRIVER:
        has_access = any(
            a.driver_id == current_user.id
            for r in plan.routes
            for a in r.assignments
        )
        if not has_access:
            raise HTTPException(status_code=403, detail="배정된 플랜이 아닙니다")
    return plan


@router.patch("/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: int,
    data: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="플랜을 찾을 수 없습니다")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(plan, k, v)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="플랜을 찾을 수 없습니다")
    db.delete(plan)
    db.commit()
