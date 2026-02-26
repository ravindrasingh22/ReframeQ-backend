from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Profile(Base):
    __tablename__ = 'profiles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    profile_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # adult | child
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    age_band: Mapped[str] = mapped_column(String(30), nullable=False, default='adult')
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
