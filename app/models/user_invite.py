from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserInvite(Base):
    __tablename__ = 'user_invites'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, nullable=False, index=True)
    invite_code: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='invited')
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
