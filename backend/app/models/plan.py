"""플랜(일정) 모델"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Plan(Base):
    """플랜(일정) - 특정 날짜의 배송 계획"""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    route: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    memo: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    routes: Mapped[list["Route"]] = relationship(
        "Route", back_populates="plan", cascade="all, delete-orphan", order_by="Route.sequence"
    )
