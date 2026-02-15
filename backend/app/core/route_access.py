"""Driver는 배정된 루트만 접근 - 권한 검사"""
from fastapi import HTTPException, status

from app.models import User, Route
from app.models.user import Role


def require_route_access(user: User, route: Route) -> None:
    """Driver는 자신이 배정된 루트만 접근 가능. ADMIN은 모든 루트 접근."""
    if user.role == Role.ADMIN:
        return
    if user.role != Role.DRIVER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다")
    assigned = any(a.driver_id == user.id for a in route.assignments)
    if not assigned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="배정된 루트가 아닙니다")
