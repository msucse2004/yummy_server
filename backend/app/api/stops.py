"""스탑 CRUD - ADMIN 관리, DRIVER는 배정된 루트의 스탑만"""
from decimal import Decimal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.auth import require_user, require_role
from app.core.route_access import require_route_access
from app.database import get_db
from app.models import User, Route, Stop, StopOrderItem, Customer, Item, StopCompletion, AppSetting, Plan
from app.models.user import Role
from app.schemas.stop import StopCreate, StopUpdate, StopResponse, StopOrderItemResponse

router = APIRouter(prefix="/api/stops", tags=["stops"])
RequireAdmin = Depends(require_role(Role.ADMIN))

_SETTING_KEYS = [
    "company_name", "company_address", "company_phone",
    "business_registration_number", "representative_name",
    "business_type", "business_category",
    "bank_name", "bank_account", "bank_holder",
]


def _get_settings_dict(db: Session) -> dict:
    rows = db.execute(select(AppSetting).where(AppSetting.key.in_(_SETTING_KEYS))).scalars().all()
    return {r.key: (r.value or "") for r in rows}


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
            joinedload(Stop.completions).joinedload(StopCompletion.photos),
        )
    )
    return list(db.execute(stmt).scalars().unique().all())


class ReorderStopsRequest(BaseModel):
    stop_ids: list[int] = Field(..., min_length=1)


@router.put("/route/{route_id}/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_stops(
    route_id: int,
    data: ReorderStopsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """스탑 순서 변경 (stop_ids 순서대로 sequence 부여)"""
    route = _get_route_with_assignments(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="루트를 찾을 수 없습니다")
    for seq, stop_id in enumerate(data.stop_ids):
        stop = db.get(Stop, stop_id)
        if not stop or stop.route_id != route_id:
            raise HTTPException(status_code=400, detail=f"스탑 ID {stop_id}를 찾을 수 없거나 해당 루트가 아닙니다")
        stop.sequence = seq
    db.commit()


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


def _calc_receipt_line(quantity: float, unit_price: float | None) -> tuple[int, int]:
    """금액(공급가액), 세액 계산. 단가는 세금 포함 가정 (VAT 10%)"""
    if unit_price is None or quantity <= 0:
        return 0, 0
    total = int(Decimal(str(quantity)) * Decimal(str(unit_price)))
    supply = round(total / Decimal("1.1"))  # 공급가액 (반올림)
    tax = total - supply  # 세액
    return supply, tax


def calc_stop_total(stop: Stop) -> int:
    """스탑 주문 총액 (공급가+세액) - 배송 완료 시 미수금 반영용"""
    total = 0
    for oi in stop.order_items:
        item = oi.item if oi else None
        if item:
            supply, tax = _calc_receipt_line(float(oi.quantity), item.unit_price)
            total += supply + tax
    return total


def add_arrears_for_completed_stop(db: Session, stop: Stop) -> None:
    """배송 완료 시 거래처 미수금에 스탑 금액 반영"""
    total = calc_stop_total(stop)
    if total > 0 and stop.customer_id and stop.customer:
        prev = int(stop.customer.arrears or 0)
        stop.customer.arrears = prev + total


class ReceiptItemRow(BaseModel):
    product_spec: str  # 품목(규격) - 코드 상품명 등
    unit: str = ""
    quantity: int | float = 0
    unit_price: int = 0
    supply_amount: int = 0
    tax_amount: int = 0


class ReceiptResponse(BaseModel):
    doc_no: str
    date_str: str
    supplier: dict
    buyer: dict
    bank_info: str
    items: list[ReceiptItemRow]
    supply_total: int
    tax_total: int
    total: int
    prev_arrears: int = 0
    arrears: int


@router.get("/{stop_id}/receipt", response_model=ReceiptResponse)
def get_stop_receipt(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """거래명세표용 영수증 데이터"""
    stop = db.get(
        Stop,
        stop_id,
        options=[
            joinedload(Stop.route).joinedload(Route.plan),
            joinedload(Stop.order_items).joinedload(StopOrderItem.item),
            joinedload(Stop.customer),
        ],
    )
    if not stop or not stop.customer:
        raise HTTPException(status_code=404, detail="스탑을 찾을 수 없습니다")
    require_route_access(current_user, stop.route)

    settings_dict = _get_settings_dict(db)
    plan = stop.route.plan if stop.route else None
    plan_date: date = plan.plan_date if plan else date.today()

    supplier = {
        "business_registration_number": settings_dict.get("business_registration_number", ""),
        "name": settings_dict.get("company_name", ""),
        "representative_name": settings_dict.get("representative_name", ""),
        "address": settings_dict.get("company_address", ""),
        "business_type": settings_dict.get("business_type", ""),
        "business_category": settings_dict.get("business_category", ""),
    }

    buyer = {
        "business_registration_number": stop.customer.business_registration_number or "",
        "name": stop.customer.name or "",
        "representative_name": stop.customer.representative_name or "",
        "address": stop.customer.address or "",
        "business_type": stop.customer.business_type or "",
        "business_category": stop.customer.business_category or "",
    }

    bank_parts = []
    if settings_dict.get("bank_name"):
        bank_parts.append(settings_dict["bank_name"])
    if settings_dict.get("bank_account"):
        bank_parts.append(settings_dict["bank_account"])
    holder = settings_dict.get("bank_holder") or settings_dict.get("representative_name", "")
    comp = settings_dict.get("company_name", "")
    if holder and comp:
        bank_parts.append(f"{holder}({comp})")
    elif holder:
        bank_parts.append(holder)
    bank_info = " ".join(bank_parts) if bank_parts else ""

    items: list[ReceiptItemRow] = []
    supply_total = 0
    tax_total = 0
    for oi in stop.order_items:
        item = oi.item
        if not item:
            continue
        up = int(oi.quantity * (item.unit_price or 0)) if item.unit_price else 0
        unit_price_display = int(item.unit_price or 0)
        supply, tax = _calc_receipt_line(float(oi.quantity), item.unit_price)
        parts = [item.code or "", item.product or ""]
        if item.description:
            parts.append(str(item.description))
        if item.weight:
            parts.append(f"({item.weight}kg{item.unit or ''})")
        product_spec = " ".join(str(p) for p in parts if p).strip()

        supply_total += supply
        tax_total += tax
        items.append(ReceiptItemRow(
            product_spec=product_spec,
            unit=item.unit or "",
            quantity=float(oi.quantity),
            unit_price=unit_price_display,
            supply_amount=supply,
            tax_amount=tax,
        ))

    total = supply_total + tax_total
    customer_arrears = int(stop.customer.arrears or 0)
    # 거래명세표는 항상 배송전 관점: 배송완료 시 customer.arrears에 이미 합계가 반영된 상태이므로 역산
    if stop.is_completed and customer_arrears >= total:
        prev_arrears = customer_arrears - total  # 배송 전 전미수
    else:
        prev_arrears = customer_arrears
    arrears = prev_arrears + total

    doc_no = f"{plan_date.strftime('%m%d')}-{stop_id:04d}"

    return ReceiptResponse(
        doc_no=doc_no,
        date_str=plan_date.strftime("%Y년 %m월 %d일"),
        supplier=supplier,
        buyer=buyer,
        bank_info=bank_info,
        items=items,
        supply_total=supply_total,
        tax_total=tax_total,
        total=total,
        prev_arrears=prev_arrears,
        arrears=arrears,
    )


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
