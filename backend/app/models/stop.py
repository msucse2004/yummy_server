"""스탑(배송지) 모델"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StopOrderItem(Base):
    """스탑별 주문 품목/수량"""

    __tablename__ = "stop_order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stop_id: Mapped[int] = mapped_column(ForeignKey("stops.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=1)
    memo: Mapped[str | None] = mapped_column(String(256), nullable=True)

    stop: Mapped["Stop"] = relationship("Stop", back_populates="order_items")
    item: Mapped["Item"] = relationship("Item")


class Stop(Base):
    """스탑 - 루트 내 배송지"""

    __tablename__ = "stops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    route: Mapped["Route"] = relationship("Route", back_populates="stops")
    customer: Mapped["Customer"] = relationship("Customer")
    order_items: Mapped[list["StopOrderItem"]] = relationship(
        "StopOrderItem", back_populates="stop", cascade="all, delete-orphan"
    )
    completions: Mapped[list["StopCompletion"]] = relationship(
        "StopCompletion", back_populates="stop", cascade="all, delete-orphan"
    )

    @property
    def is_completed(self) -> bool:
        return len(self.completions) > 0
