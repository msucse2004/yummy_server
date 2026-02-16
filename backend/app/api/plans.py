"""플랜 CRUD - ADMIN 생성/수정, DRIVER는 배정된 플랜만 조회"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.auth import require_user, require_role
from app.database import get_db
from app.models import User, Plan, Route, RouteAssignment, Stop, StopOrderItem, Item, Customer, StopCompletion
from app.models.user import Role
from app.schemas.plan import PlanCreate, PlanListResponse, PlanUpdate, PlanResponse
from app.services.contract_match import contract_items_to_display_string, match_contract_content

router = APIRouter(prefix="/api/plans", tags=["plans"])
RequireAdmin = Depends(require_role(Role.ADMIN))


def _get_plan_delivery_status(db: Session, plan_id: int) -> str:
    """플랜의 배송 상태: 배송전 / 배송중(k/n) / 배송완료"""
    total = db.execute(
        select(func.count(Stop.id))
        .select_from(Stop)
        .join(Route, Stop.route_id == Route.id)
        .where(Route.plan_id == plan_id)
    ).scalar() or 0
    if total == 0:
        return "배송전"
    completed = db.execute(
        select(func.count(distinct(Stop.id)))
        .select_from(Stop)
        .join(Route, Stop.route_id == Route.id)
        .join(StopCompletion, Stop.id == StopCompletion.stop_id)
        .where(Route.plan_id == plan_id)
    ).scalar() or 0
    if completed == 0:
        return "배송전"
    if completed >= total:
        return "배송완료"
    return f"배송중({completed}/{total})"


def _get_route_delivery_status(db: Session, route_id: int, route: Route | None = None) -> str:
    """단일 루트의 배송 상태: 배송전 / 배송시작 / 배송중(k/n) / 배송완료"""
    total = db.execute(
        select(func.count(Stop.id)).select_from(Stop).where(Stop.route_id == route_id)
    ).scalar() or 0
    if total == 0:
        return "배송전"
    completed = db.execute(
        select(func.count(distinct(Stop.id)))
        .select_from(Stop)
        .join(StopCompletion, Stop.id == StopCompletion.stop_id)
        .where(Stop.route_id == route_id)
    ).scalar() or 0
    if completed == 0:
        r = route or db.get(Route, route_id)
        if r and r.started_at:
            return "배송시작"
        return "배송전"
    if completed >= total:
        return "배송완료"
    return f"배송중({completed}/{total})"


def _get_plan_route_delivery_statuses(db: Session, plan_id: int) -> str:
    """플랜의 루트별 배송상태 문자열: 1호차: 배송전, 2호차: 배송중(1/N), 3호차: 배송완료"""
    routes = list(
        db.scalars(
            select(Route).where(Route.plan_id == plan_id).order_by(Route.sequence.asc(), Route.id.asc())
        ).all()
    )
    if not routes:
        return _get_plan_delivery_status(db, plan_id)
    parts = []
    for route in routes:
        label = (route.name or str(route.id)).strip() or f"루트{route.id}"
        status = _get_route_delivery_status(db, route.id, route)
        parts.append(f"{label}: {status}")
    return ", ".join(parts)


def _auto_assign_drivers_by_department(db: Session, plan_id: int) -> None:
    """부서(루트명) 매칭으로 기사 자동 배정. 배정 없는 루트만 채움."""
    plan = db.get(
        Plan,
        plan_id,
        options=[joinedload(Plan.routes).joinedload(Route.assignments)],
    )
    if not plan:
        return
    drivers_by_dept: dict[str, list[User]] = defaultdict(list)
    for u in db.execute(
        select(User).where(User.role == Role.DRIVER, User.status == "재직")
    ).scalars().all():
        if u.department and str(u.department).strip():
            drivers_by_dept[str(u.department).strip()].append(u)
    for route in plan.routes:
        if route.assignments:
            continue
        route_name = (route.name or "").strip()
        candidates = drivers_by_dept.get(route_name) if route_name else None
        if candidates:
            db.add(RouteAssignment(route_id=route.id, driver_id=candidates[0].id))
    db.flush()


def _get_plan_delivery_summary(db: Session, plan_id: int) -> tuple[str, int]:
    """플랜의 배달 수량(곱슬이 10박스, ...), 일일매출(원) 반환"""
    stmt = (
        select(Item.product, Item.unit, StopOrderItem.quantity, Item.unit_price)
        .select_from(StopOrderItem)
        .join(Item, StopOrderItem.item_id == Item.id)
        .join(Stop, StopOrderItem.stop_id == Stop.id)
        .join(Route, Stop.route_id == Route.id)
        .where(Route.plan_id == plan_id)
    )
    rows = db.execute(stmt).all()
    agg: dict[tuple[str, str], float] = defaultdict(float)
    daily_sales = 0
    for product, unit, qty, price in rows:
        key = (product or "", unit or "박스")
        agg[key] += float(qty)
        if price is not None:
            daily_sales += int(float(qty) * float(price))
    parts = [f"{p} {int(q) if q == int(q) else q}{u}" for (p, u), q in sorted(agg.items())]
    return ", ".join(parts), daily_sales


@router.get("", response_model=list[PlanListResponse])
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
    plans = list(db.execute(stmt).scalars().unique().all())
    result = []
    for p in plans:
        delivery_qty, daily_sales = _get_plan_delivery_summary(db, p.id)
        delivery_status = _get_plan_route_delivery_statuses(db, p.id)
        result.append(
            PlanListResponse(
                id=p.id,
                plan_date=p.plan_date,
                route=p.route,
                name=p.name,
                memo=p.memo,
                delivery_quantity=delivery_qty,
                daily_sales=daily_sales,
                delivery_status=delivery_status,
            )
        )
    return result


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


class NewPlanCustomerRow(BaseModel):
    customer_id: int
    code: str
    route: str
    name: str
    delivery_items: str = ""


class CreatePlanFromListRequest(BaseModel):
    plan_date: date
    rows: list[NewPlanCustomerRow] = Field(..., min_length=1)


@router.get("/new-plan-defaults")
def get_new_plan_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """새 플랜 폼 기본값: 내일 날짜, 거래처 목록(배달 항목은 최근 플랜 또는 계약내용)"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    customers = list(db.execute(select(Customer).order_by(Customer.route, Customer.name)).scalars().all())
    latest_stmt = (
        select(Plan)
        .order_by(Plan.plan_date.desc())
        .limit(1)
        .options(
            joinedload(Plan.routes).joinedload(Route.stops).joinedload(Stop.order_items).joinedload(StopOrderItem.item),
        )
    )
    latest_plan = db.execute(latest_stmt).scalars().unique().first()
    customer_delivery: dict[int, str] = {}
    if latest_plan:
        for route in latest_plan.routes:
            for stop in route.stops:
                items = []
                for oi in stop.order_items:
                    if oi.item:
                        q = float(oi.quantity)
                        items.append(
                            f"{oi.item.product} {int(q) if q == int(q) else q}{oi.item.unit}"
                        )
                if items:
                    customer_delivery[stop.customer_id] = ", ".join(items)
    rows = []
    for c in customers:
        delivery = customer_delivery.get(c.id) or c.contract_content or ""
        rows.append(
            NewPlanCustomerRow(
                customer_id=c.id,
                code=c.code or "",
                route=c.route or "",
                name=c.name or "",
                delivery_items=delivery,
            )
        )
    return {"plan_date": tomorrow, "rows": rows}


@router.get("/{plan_id}/edit-data")
def get_plan_edit_data(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """플랜 수정용 데이터 - 새플랜 폼과 동일 형식"""
    plan = db.get(
        Plan,
        plan_id,
        options=[
            joinedload(Plan.routes).joinedload(Route.stops).joinedload(Stop.order_items).joinedload(StopOrderItem.item),
            joinedload(Plan.routes).joinedload(Route.stops).joinedload(Stop.customer),
        ],
    )
    if not plan:
        raise HTTPException(status_code=404, detail="플랜을 찾을 수 없습니다")
    rows = []
    for route in sorted(plan.routes, key=lambda r: (r.sequence, r.id)):
        for stop in sorted(route.stops, key=lambda s: (s.sequence, s.id)):
            items = []
            for oi in stop.order_items:
                if oi.item:
                    q = float(oi.quantity)
                    items.append(
                        f"{oi.item.product} {int(q) if q == int(q) else q}{oi.item.unit}"
                    )
            rows.append(
                NewPlanCustomerRow(
                    customer_id=stop.customer_id,
                    code=stop.customer.code or "",
                    route=route.name,
                    name=stop.customer.name or "",
                    delivery_items=", ".join(items),
                )
            )
    return {"plan_date": plan.plan_date.isoformat(), "rows": rows, "plan_id": plan_id}


@router.put("/{plan_id}/update-from-list", response_model=PlanResponse)
def update_plan_from_list(
    plan_id: int,
    data: CreatePlanFromListRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """거래처 목록 기반으로 플랜 업데이트 (기존 루트/스탑 삭제 후 재생성)"""
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="플랜을 찾을 수 없습니다")
    if data.plan_date != plan.plan_date:
        existing = (
            db.execute(select(Plan).where(Plan.plan_date == data.plan_date, Plan.id != plan_id))
            .scalars()
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"해당 날짜({data.plan_date})에 이미 배송 플랜이 있습니다. 다른 날짜를 선택하세요.",
            )
    for route in list(plan.routes):
        db.delete(route)
    db.flush()
    plan.plan_date = data.plan_date
    plan.name = f"{data.plan_date} 배달"
    by_route: dict[str, list[NewPlanCustomerRow]] = defaultdict(list)
    for r in data.rows:
        rt = r.route.strip() or "기타"
        by_route[rt].append(r)
    for seq, (route_name, rows) in enumerate(sorted(by_route.items())):
        route = Route(plan_id=plan.id, name=route_name, sequence=seq)
        db.add(route)
        db.flush()
        for sidx, row in enumerate(rows):
            matches = match_contract_content(row.delivery_items, db)
            order_items_data = [
                {"item_id": m["item_id"], "quantity": Decimal(str(m["quantity"])), "memo": None}
                for m in matches
            ]
            if not order_items_data:
                order_items_data = []
            stop = Stop(route_id=route.id, customer_id=row.customer_id, sequence=sidx, memo=None)
            db.add(stop)
            db.flush()
            for oi in order_items_data:
                db.add(
                    StopOrderItem(
                        stop_id=stop.id,
                        item_id=oi["item_id"],
                        quantity=oi["quantity"],
                        memo=oi["memo"],
                    )
                )
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/create-from-list", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan_from_list(
    data: CreatePlanFromListRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """거래처 목록 기반으로 플랜 생성 (루트별 Route, Stop, order_items)"""
    existing = db.execute(select(Plan).where(Plan.plan_date == data.plan_date)).scalars().first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"해당 날짜({data.plan_date})에 이미 배송 플랜이 있습니다. 다른 날짜를 선택하세요.",
        )
    plan = Plan(
        plan_date=data.plan_date,
        route=None,
        name=f"{data.plan_date} 배달",
        memo=None,
    )
    db.add(plan)
    db.flush()
    by_route: dict[str, list[NewPlanCustomerRow]] = defaultdict(list)
    for r in data.rows:
        rt = r.route.strip() or "기타"
        by_route[rt].append(r)
    for seq, (route_name, rows) in enumerate(sorted(by_route.items())):
        route = Route(plan_id=plan.id, name=route_name, sequence=seq)
        db.add(route)
        db.flush()
        for sidx, row in enumerate(rows):
            matches = match_contract_content(row.delivery_items, db)
            order_items_data = [
                {"item_id": m["item_id"], "quantity": Decimal(str(m["quantity"])), "memo": None}
                for m in matches
            ]
            if not order_items_data:
                order_items_data = []
            stop = Stop(route_id=route.id, customer_id=row.customer_id, sequence=sidx, memo=None)
            db.add(stop)
            db.flush()
            for oi in order_items_data:
                db.add(
                    StopOrderItem(
                        stop_id=stop.id,
                        item_id=oi["item_id"],
                        quantity=oi["quantity"],
                        memo=oi["memo"],
                    )
                )
    db.commit()
    db.refresh(plan)
    return plan


class RouteWithAssignment(BaseModel):
    """루트 + 배정 기사 정보 + 배송상태 (플랜 상세용)"""
    id: int
    plan_id: int
    name: str
    sequence: int
    assignments: list[dict] = []
    delivery_status: str = ""
    model_config = {"from_attributes": True}


class PlanDetailResponse(BaseModel):
    """플랜 상세 - 루트별 배정 + 이전날 기사 디폴트"""
    plan: PlanResponse
    routes: list[RouteWithAssignment]
    previous_day_drivers: dict[str, dict] = {}


@router.get("/{plan_id}/plan-detail", response_model=PlanDetailResponse)
def get_plan_detail(
    plan_id: int,
    auto_assign: bool = Query(True, description="배정 없는 루트에 부서 매칭으로 기사 자동 배정"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """관리자 플랜 상세 - 루트별 기사 배정, 이전날 기사 디폴트, 배송상태 포함"""
    if current_user.role == Role.ADMIN and auto_assign:
        _auto_assign_drivers_by_department(db, plan_id)
        db.commit()
    plan = db.get(
        Plan,
        plan_id,
        options=[
            joinedload(Plan.routes).joinedload(Route.assignments).joinedload(RouteAssignment.driver),
        ],
    )
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

    prev_plan = db.execute(
        select(Plan)
        .where(Plan.plan_date == plan.plan_date - timedelta(days=1))
        .order_by(Plan.id.desc())
        .limit(1)
    ).scalars().first()
    previous_day_drivers: dict[str, dict] = {}
    if prev_plan:
        prev_plan = db.get(
            Plan,
            prev_plan.id,
            options=[
                joinedload(Plan.routes).joinedload(Route.assignments).joinedload(RouteAssignment.driver),
            ],
        )
        if prev_plan and hasattr(prev_plan, "routes"):
            for r in prev_plan.routes:
                if r.assignments:
                    a = r.assignments[0]
                    d = a.driver
                    previous_day_drivers[r.name] = {
                        "driver_id": d.id,
                        "driver_name": (d.display_name or d.username) if d else "",
                    }

    routes_data = []
    for r in sorted(plan.routes, key=lambda x: (x.sequence, x.id)):
        assignments = [
            {"driver_id": a.driver_id, "driver_name": (a.driver.display_name or a.driver.username) if a.driver else ""}
            for a in r.assignments
        ]
        route_status = _get_route_delivery_status(db, r.id, r)
        routes_data.append(
            RouteWithAssignment(
                id=r.id,
                plan_id=r.plan_id,
                name=r.name,
                sequence=r.sequence,
                assignments=assignments,
                delivery_status=route_status,
            )
        )

    return PlanDetailResponse(
        plan=PlanResponse.model_validate(plan),
        routes=routes_data,
        previous_day_drivers=previous_day_drivers,
    )


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
    if data.plan_date is not None and data.plan_date != plan.plan_date:
        existing = (
            db.execute(select(Plan).where(Plan.plan_date == data.plan_date, Plan.id != plan_id))
            .scalars()
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"해당 날짜({data.plan_date})에 이미 배송 플랜이 있습니다. 다른 날짜를 선택하세요.",
            )
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
