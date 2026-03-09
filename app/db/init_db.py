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
    if 'onboarding_step' not in detail_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE user_details ADD COLUMN onboarding_step VARCHAR(64) NOT NULL DEFAULT 'welcome'"))
    if 'onboarding_completed' not in detail_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE user_details ADD COLUMN onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE"))
    if 'onboarding_state' not in detail_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE user_details ADD COLUMN onboarding_state JSON NOT NULL DEFAULT '{}'"))
    if 'onboarding_updated_at' not in detail_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE user_details ADD COLUMN onboarding_updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()"))

    invite_columns = {col['name'] for col in inspector.get_columns('user_invites')}
    if 'invite_code' not in invite_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE user_invites ADD COLUMN invite_code VARCHAR(32)"))

    mood_tables = set(inspector.get_table_names())
    if 'mood_checkins' not in mood_tables:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE mood_checkins (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        mood_id VARCHAR(32) NOT NULL,
                        mood_label VARCHAR(64) NOT NULL,
                        checkin_date DATE NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                        CONSTRAINT uq_mood_checkins_user_date UNIQUE (user_id, checkin_date)
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX ix_mood_checkins_user_id ON mood_checkins (user_id)"))
            conn.execute(text("CREATE INDEX ix_mood_checkins_checkin_date ON mood_checkins (checkin_date)"))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_schema_updates()
