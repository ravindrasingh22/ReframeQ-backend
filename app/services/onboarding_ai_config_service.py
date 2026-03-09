import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlatformSetting

FIRST_REFRAME_CONFIG_KEY = 'onboarding_ai.first_reframe'

DEFAULT_FIRST_REFRAME_CONFIG = {
    'enabled': True,
    'model_name': 'mistral',
    'temperature': 0.2,
    'max_tokens': 220,
    'schema_version': 'onboarding-first-reframe-v1',
    'show_pattern_label': True,
    'show_titles': True,
    'system_prompt': (
        'You are generating ReframeQ onboarding content for the first reframe screen. '
        'Return content for exactly these fields: pattern_label, reframe_text, next_step_text, question_text. '
        'Do not diagnose. Do not repeat the user thought. Keep each field short. '
        'next_step_text must be one concrete action. question_text must be one Socratic question.'
    ),
    'developer_prompt': '',
    'fallback_template_json': {
        'reframe_title': 'A different way to look at it',
        'next_step_title': 'Try this next',
        'question_title': 'One question to test it',
    },
    'style_overrides': {},
    'goal_overrides': {},
    'user_type_overrides': {},
    'safety_overrides': {},
}


def get_first_reframe_config(db: Session) -> dict:
    setting = db.execute(select(PlatformSetting).where(PlatformSetting.key == FIRST_REFRAME_CONFIG_KEY)).scalar_one_or_none()
    if not setting:
        return DEFAULT_FIRST_REFRAME_CONFIG.copy()
    try:
        parsed = json.loads(setting.value_json)
        merged = DEFAULT_FIRST_REFRAME_CONFIG.copy()
        merged.update(parsed if isinstance(parsed, dict) else {})
        if merged.get('model_name') in {None, '', 'llama3.1:8b'}:
            merged['model_name'] = 'mistral'
        return merged
    except json.JSONDecodeError:
        return DEFAULT_FIRST_REFRAME_CONFIG.copy()


def save_first_reframe_config(db: Session, config: dict) -> dict:
    setting = db.execute(select(PlatformSetting).where(PlatformSetting.key == FIRST_REFRAME_CONFIG_KEY)).scalar_one_or_none()
    payload = DEFAULT_FIRST_REFRAME_CONFIG.copy()
    payload.update(config)
    if not setting:
        setting = PlatformSetting(key=FIRST_REFRAME_CONFIG_KEY, value_json=json.dumps(payload))
        db.add(setting)
    else:
        setting.value_json = json.dumps(payload)
    db.commit()
    return payload
