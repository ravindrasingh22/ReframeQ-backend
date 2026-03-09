from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MoodCheckin(Base):
    __tablename__ = 'mood_checkins'
    __table_args__ = (UniqueConstraint('user_id', 'checkin_date', name='uq_mood_checkins_user_date'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    mood_id: Mapped[str] = mapped_column(String(32), nullable=False)
    mood_label: Mapped[str] = mapped_column(String(64), nullable=False)
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
