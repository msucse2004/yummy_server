"""기사 완료/사진 모델"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StopCompletion(Base):
    """스탑 완료 처리 (기사가 배송 완료 시)"""

    __tablename__ = "stop_completions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stop_id: Mapped[int] = mapped_column(ForeignKey("stops.id", ondelete="CASCADE"), nullable=False)
    completed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)

    stop: Mapped["Stop"] = relationship("Stop", back_populates="completions")
    photos: Mapped[list["Photo"]] = relationship(
        "Photo", back_populates="completion", cascade="all, delete-orphan"
    )


class Photo(Base):
    """완료 시 업로드된 사진"""

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    completion_id: Mapped[int] = mapped_column(
        ForeignKey("stop_completions.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    completion: Mapped["StopCompletion"] = relationship("StopCompletion", back_populates="photos")
