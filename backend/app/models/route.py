"""루트 모델"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Route(Base):
    """루트 - 플랜 내 배송 경로"""

    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    plan: Mapped["Plan"] = relationship("Plan", back_populates="routes")
    assignments: Mapped[list["RouteAssignment"]] = relationship(
        "RouteAssignment", back_populates="route", cascade="all, delete-orphan"
    )
    stops: Mapped[list["Stop"]] = relationship(
        "Stop", back_populates="route", cascade="all, delete-orphan", order_by="Stop.sequence"
    )


class RouteAssignment(Base):
    """루트-기사 배정 (Driver는 assigned route만 접근)"""

    __tablename__ = "route_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    route: Mapped["Route"] = relationship("Route", back_populates="assignments")
    driver: Mapped["User"] = relationship("User", back_populates="route_assignments")
