import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permissions
from app.db.session import get_db
from app.models import AuditLog, PlatformSetting
from app.schemas.settings import LanguageOption, SupportedLanguagesResponse, UpdateSupportedLanguagesRequest

router = APIRouter()
SUPPORTED_LANGUAGES_KEY = 'supported_languages'
ISO_LANGUAGE_NAMES = {
    'ar': 'Arabic',
    'bn': 'Bengali',
    'de': 'German',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'hi': 'Hindi',
    'it': 'Italian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'mr': 'Marathi',
    'nl': 'Dutch',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'sv': 'Swedish',
    'ta': 'Tamil',
    'te': 'Telugu',
    'tr': 'Turkish',
    'ur': 'Urdu',
    'zh': 'Chinese',
}
DEFAULT_LANGUAGE_OPTIONS = [{'code': 'en', 'name': 'English', 'enabled': True}]


def _normalize_iso_code(value: str) -> str:
    return str(value).strip().lower()


def _coerce_to_language_options(values: list[object]) -> list[dict[str, object]]:
    options: list[dict[str, object]] = []
    seen: set[str] = set()

    for item in values:
        if isinstance(item, dict):
            code = _normalize_iso_code(item.get('code', ''))
            enabled = bool(item.get('enabled', True))
        else:
            raw = _normalize_iso_code(item)
            legacy_map = {'english': 'en'}
            code = legacy_map.get(raw, raw)
            enabled = True

        if code not in ISO_LANGUAGE_NAMES or code in seen:
            continue

        options.append({'code': code, 'name': ISO_LANGUAGE_NAMES[code], 'enabled': enabled})
        seen.add(code)

    if 'en' not in seen:
        options.append({'code': 'en', 'name': ISO_LANGUAGE_NAMES['en'], 'enabled': True})

    return options


def _load_language_options(db: Session) -> tuple[PlatformSetting, list[dict[str, object]]]:
    setting = db.execute(
        select(PlatformSetting).where(PlatformSetting.key == SUPPORTED_LANGUAGES_KEY)
    ).scalar_one_or_none()

    if not setting:
        setting = PlatformSetting(key=SUPPORTED_LANGUAGES_KEY, value_json=json.dumps(DEFAULT_LANGUAGE_OPTIONS))
        db.add(setting)
        db.commit()
        db.refresh(setting)
        return setting, DEFAULT_LANGUAGE_OPTIONS

    try:
        values = json.loads(setting.value_json)
        if not isinstance(values, list):
            values = []
    except json.JSONDecodeError:
        values = []

    options = _coerce_to_language_options(values)
    if options != values:
        setting.value_json = json.dumps(options)
        db.add(setting)
        db.commit()
        db.refresh(setting)

    return setting, options


def get_supported_languages(db: Session) -> list[str]:
    _, options = _load_language_options(db)
    enabled = [str(item['code']) for item in options if bool(item.get('enabled'))]
    return enabled or ['en']


@router.get('/languages', response_model=SupportedLanguagesResponse)
def list_supported_languages(
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.read'))],
    db: Annotated[Session, Depends(get_db)],
) -> SupportedLanguagesResponse:
    _, options = _load_language_options(db)
    enabled = [str(item['code']) for item in options if bool(item.get('enabled'))]
    return SupportedLanguagesResponse(
        supported_languages=enabled or ['en'],
        options=[
            LanguageOption(code=str(item['code']), name=str(item['name']), enabled=bool(item['enabled']))
            for item in options
        ],
    )


@router.put('/languages', response_model=SupportedLanguagesResponse)
def update_supported_languages(
    payload: UpdateSupportedLanguagesRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.write'))],
    db: Annotated[Session, Depends(get_db)],
) -> SupportedLanguagesResponse:
    normalized: list[str] = []
    for value in payload.supported_languages:
        code = _normalize_iso_code(value)
        if not code:
            continue
        if code not in ISO_LANGUAGE_NAMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Unsupported ISO language code: {code}',
            )
        if code not in normalized:
            normalized.append(code)

    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='At least one language is required')

    setting, existing_options = _load_language_options(db)
    option_map = {str(item['code']): bool(item.get('enabled')) for item in existing_options}
    for code in normalized:
        if code not in option_map:
            option_map[code] = True

    updated_codes = sorted(option_map.keys())
    updated_options = [
        {'code': code, 'name': ISO_LANGUAGE_NAMES[code], 'enabled': code in normalized}
        for code in updated_codes
    ]
    if not any(option['enabled'] for option in updated_options):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='At least one language must stay enabled')

    setting.value_json = json.dumps(updated_options)

    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='supported_languages_updated',
            module='settings',
            details=f'enabled_languages={normalized}',
        )
    )
    db.commit()
    return SupportedLanguagesResponse(
        supported_languages=normalized,
        options=[
            LanguageOption(code=str(item['code']), name=str(item['name']), enabled=bool(item['enabled']))
            for item in updated_options
        ],
    )
