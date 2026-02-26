from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserDetail(Base):
    __tablename__ = 'user_details'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False, default='')
    country: Mapped[str] = mapped_column(String(80), nullable=False, default='')
    language: Mapped[str] = mapped_column(String(40), nullable=False, default='en')
