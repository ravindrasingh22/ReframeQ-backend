from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserDetail(Base):
    __tablename__ = 'user_details'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False, default='')
    mobile_country_code: Mapped[str] = mapped_column(String(12), nullable=False, default='')
    mobile_number: Mapped[str] = mapped_column(String(24), nullable=False, default='')
    city: Mapped[str] = mapped_column(String(120), nullable=False, default='')
    state: Mapped[str] = mapped_column(String(120), nullable=False, default='')
    country: Mapped[str] = mapped_column(String(80), nullable=False, default='')
    language: Mapped[str] = mapped_column(String(40), nullable=False, default='en')
    onboarding_step: Mapped[str] = mapped_column(String(64), nullable=False, default='welcome')
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    onboarding_state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    onboarding_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
