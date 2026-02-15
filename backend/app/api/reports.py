"""월말 정산 리포트 PDF - ADMIN 전용"""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.auth import require_user, require_role
from app.database import get_db
from app.models import User, StopCompletion, Stop, Route, Plan, Customer
from app.models.user import Role
from app.services.report import generate_monthly_report_pdf

router = APIRouter(prefix="/api/reports", tags=["reports"])
RequireAdmin = Depends(require_role(Role.ADMIN))


@router.get("/monthly/pdf")
def monthly_report_pdf(
    year: Annotated[int, Query(ge=2020, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    _: User = RequireAdmin,
):
    """월말 정산 리포트 PDF 다운로드"""
    from datetime import date as date_type
    from calendar import monthrange

    start = date_type(year, month, 1)
    _, last = monthrange(year, month)
    end = date_type(year, month, last)

    stmt = (
        select(StopCompletion, Stop, Route, Plan, Customer)
        .join(Stop, StopCompletion.stop_id == Stop.id)
        .join(Route, Stop.route_id == Route.id)
        .join(Plan, Route.plan_id == Plan.id)
        .join(Customer, Stop.customer_id == Customer.id)
        .where(Plan.plan_date >= start, Plan.plan_date <= end)
        .order_by(Plan.plan_date, Route.sequence, Stop.sequence)
    )
    rows = db.execute(stmt).all()

    completions = []
    driver_counts: dict[str, dict] = {}
    for comp, stop, route, plan, customer in rows:
        driver_name = "미확인"
        if comp.completed_by_user_id:
            u = db.get(User, comp.completed_by_user_id)
            driver_name = u.display_name or u.username if u else "미확인"
        completions.append({
            "plan_date": plan.plan_date,
            "route_name": route.name,
            "customer_name": customer.name,
            "driver_name": driver_name,
            "completed_at": comp.completed_at,
        })
        if driver_name not in driver_counts:
            driver_counts[driver_name] = {"count": 0, "memo": ""}
        driver_counts[driver_name]["count"] += 1

    buf = generate_monthly_report_pdf(start, end, completions, driver_counts)
    filename = f"monthly_report_{year}{month:02d}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
