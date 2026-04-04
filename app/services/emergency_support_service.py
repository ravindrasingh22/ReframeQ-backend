import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlatformSetting, UserDetail

EMERGENCY_SUPPORT_CONFIGURATION_KEY = 'admin.emergency_support_configuration'

DEFAULT_EMERGENCY_SUPPORT_CONFIGURATION: dict[str, Any] = {
    'enabled': True,
    'risk_keywords': {
        'medium': [
            "can't cope",
            'cannot cope',
            'hopeless',
            'nothing matters',
            'need help',
            'need support',
            'need a therapist',
            'need a psychiatrist',
            'feel broken',
            'unable to function',
        ],
        'high': [
            "can't go on",
            'cannot go on',
            'not safe',
            'need immediate help',
            'hurt myself',
            'stay alive',
            'stay safe',
            'want to disappear',
        ],
        'critical': [
            'kill myself',
            'end my life',
            'suicide',
            'self harm',
            'self-harm',
            'die tonight',
            'hurt myself right now',
            'cannot stay safe',
        ],
    },
    'copy': {
        'profile_title': 'Emergency Support Path',
        'profile_description': 'Add trusted people and support options so help is easier to reach in a hard moment.',
        'reminder_title': 'Complete your support setup',
        'reminder_body': 'Add at least one trusted contact so ReframeQ can show the fastest support options when needed.',
        'heightened_support_title': 'You may need human support soon',
        'heightened_support_body': 'It sounds like things feel very heavy right now. If it helps, reach out to a trusted person or support service.',
        'urgent_title': 'We are concerned you may need immediate human support',
        'urgent_body': 'You do not have to handle this alone. ReframeQ is not an emergency service. Please contact a trusted person, a support helpline, or emergency help right now.',
        'safe_for_now_label': 'I am safe for now',
    },
    'resources': [
        {
            'country': 'India',
            'helpline_label': 'Call Tele-MANAS',
            'helpline_numbers': ['14416', '1-800-89-14416'],
            'emergency_label': 'Call Emergency',
            'emergency_number': '112',
            'support_search_url': 'https://www.google.com/search?q=nearby+mental+health+support',
        }
    ],
    'trusted_contact_rules': {
        'min_contacts': 1,
        'max_contacts': 3,
        'show_call_shortcut': True,
    },
    'prompts': {
        'heightened_support_reply': 'I am sorry this feels so heavy. Let us keep this simple and focus on getting you support from a person right now.',
        'urgent_reply': 'I am concerned you may need human support right now. Please contact a trusted person, a support helpline, or emergency help as soon as you can.',
        'danger_reply': 'I am concerned about your safety right now. Please call emergency help or a support helpline right away, and contact someone you trust if possible.',
    },
    'review_rules': {
        'enabled': True,
        'log_detection_events': True,
    },
}


def _deep_merge(default: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    merged = default.copy()
    for key, item in value.items():
        if isinstance(item, dict) and isinstance(default.get(key), dict):
            merged[key] = _deep_merge(default[key], item)
        else:
            merged[key] = item
    return merged


def load_emergency_support_configuration(db: Session) -> dict[str, Any]:
    setting = db.execute(
        select(PlatformSetting).where(PlatformSetting.key == EMERGENCY_SUPPORT_CONFIGURATION_KEY)
    ).scalar_one_or_none()
    if not setting:
        setting = PlatformSetting(
            key=EMERGENCY_SUPPORT_CONFIGURATION_KEY,
            value_json=json.dumps(DEFAULT_EMERGENCY_SUPPORT_CONFIGURATION),
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
        return DEFAULT_EMERGENCY_SUPPORT_CONFIGURATION.copy()
    try:
        payload = json.loads(setting.value_json)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    merged = _deep_merge(DEFAULT_EMERGENCY_SUPPORT_CONFIGURATION, payload)
    if merged != payload:
        setting.value_json = json.dumps(merged)
        db.add(setting)
        db.commit()
    return merged


def save_emergency_support_configuration(db: Session, value: dict[str, Any]) -> dict[str, Any]:
    merged = _deep_merge(DEFAULT_EMERGENCY_SUPPORT_CONFIGURATION, value)
    setting = db.execute(
        select(PlatformSetting).where(PlatformSetting.key == EMERGENCY_SUPPORT_CONFIGURATION_KEY)
    ).scalar_one_or_none()
    if not setting:
        setting = PlatformSetting(
            key=EMERGENCY_SUPPORT_CONFIGURATION_KEY,
            value_json=json.dumps(merged),
        )
        db.add(setting)
    else:
        setting.value_json = json.dumps(merged)
    db.commit()
    return merged


def _default_support_state() -> dict[str, Any]:
    return {'trusted_contacts': []}


def load_emergency_support_state(detail: UserDetail | None) -> dict[str, Any]:
    if not detail or not isinstance(detail.onboarding_state, dict):
        return _default_support_state()
    payload = detail.onboarding_state.get('emergency_support')
    if not isinstance(payload, dict):
        return _default_support_state()
    contacts = payload.get('trusted_contacts', [])
    if not isinstance(contacts, list):
        contacts = []
    return {'trusted_contacts': contacts}


def save_emergency_support_state(detail: UserDetail, trusted_contacts: list[dict[str, Any]]) -> dict[str, Any]:
    state = detail.onboarding_state if isinstance(detail.onboarding_state, dict) else {}
    normalized_contacts: list[dict[str, Any]] = []
    for item in trusted_contacts[:3]:
        name = str(item.get('name', '')).strip()
        if not name:
            continue
        normalized_contacts.append(
            {
                'id': str(item.get('id') or uuid.uuid4()),
                'name': name,
                'relationship': str(item.get('relationship', '')).strip(),
                'phone_number': str(item.get('phone_number', '')).strip(),
                'email': str(item.get('email', '')).strip(),
                'preferred_language': str(item.get('preferred_language', 'en')).strip() or 'en',
                'city': str(item.get('city', '')).strip(),
                'state': str(item.get('state', '')).strip(),
                'is_primary': bool(item.get('is_primary', False)),
                'show_call_shortcut': bool(item.get('show_call_shortcut', True)),
                'support_note': str(item.get('support_note', '')).strip(),
                'active': bool(item.get('active', True)),
            }
        )
    if normalized_contacts and not any(item['is_primary'] for item in normalized_contacts):
        normalized_contacts[0]['is_primary'] = True
    state['emergency_support'] = {'trusted_contacts': normalized_contacts}
    detail.onboarding_state = state
    return state['emergency_support']


def select_emergency_resource(config: dict[str, Any], country: str | None) -> dict[str, Any]:
    resources = config.get('resources', [])
    normalized = (country or '').strip().lower()
    for item in resources:
        if str(item.get('country', '')).strip().lower() == normalized:
            return item
    return resources[0] if resources else {}
