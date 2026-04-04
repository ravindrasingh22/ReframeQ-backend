import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlatformSetting

APP_SESSION_CONFIGURATION_KEY = 'admin.app_session_configuration'
DEFAULT_APP_SESSION_CONFIGURATION = {
    'app_session_duration_days': 30,
}


def load_app_session_configuration(db: Session) -> dict[str, int]:
    setting = db.execute(
        select(PlatformSetting).where(PlatformSetting.key == APP_SESSION_CONFIGURATION_KEY)
    ).scalar_one_or_none()
    if not setting:
        setting = PlatformSetting(
            key=APP_SESSION_CONFIGURATION_KEY,
            value_json=json.dumps(DEFAULT_APP_SESSION_CONFIGURATION),
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
        return DEFAULT_APP_SESSION_CONFIGURATION.copy()

    try:
        payload = json.loads(setting.value_json)
    except json.JSONDecodeError:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    duration_days = int(payload.get('app_session_duration_days', DEFAULT_APP_SESSION_CONFIGURATION['app_session_duration_days']) or 30)
    if duration_days < 1:
        duration_days = 1
    if duration_days > 365:
        duration_days = 365

    normalized = {'app_session_duration_days': duration_days}
    if normalized != payload:
        setting.value_json = json.dumps(normalized)
        db.add(setting)
        db.commit()

    return normalized

