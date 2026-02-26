from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Journey(Base):
    __tablename__ = 'journeys'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    topic: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default='beginner')
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default='')
