from sqlalchemy import inspect, text

from app.db.session import engine
from app.models import Base


def _apply_lightweight_schema_updates() -> None:
    inspector = inspect(engine)

    user_columns = {col['name'] for col in inspector.get_columns('users')}
    if 'created_at' not in user_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL"))

    detail_columns = {col['name'] for col in inspector.get_columns('user_details')}
    if 'full_name' not in detail_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE user_details ADD COLUMN full_name VARCHAR(120) NOT NULL DEFAULT ''"))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_schema_updates()
