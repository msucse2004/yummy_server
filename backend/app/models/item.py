"""품목 모델"""
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Item(Base):
    """품목 - 코드는 자동 생성"""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    product: Mapped[str] = mapped_column(String(128), nullable=False, index=True)  # 상품
    weight: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)  # 무게
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="박스")  # 단위: 박스, 판, 관
    unit_price: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)  # 단가
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)  # 설명
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
