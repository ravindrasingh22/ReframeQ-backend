from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GuardianLink(Base):
    __tablename__ = 'guardian_links'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    guardian_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    child_profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'), nullable=False, unique=True, index=True)
    consent_granted: Mapped[bool] = mapped_column(nullable=False, default=False)
    consent_text_version: Mapped[str] = mapped_column(String(30), nullable=False, default='v1')
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    daily_time_limit_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    topic_restrictions_json: Mapped[str] = mapped_column(Text, nullable=False, default='[]')
    conversation_visibility_rule: Mapped[str] = mapped_column(String(40), nullable=False, default='summary_only')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
