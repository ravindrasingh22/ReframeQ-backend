import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permissions
from app.db.session import get_db
from app.models import AuditLog, PlatformSetting
from app.schemas.settings import (
    AccountModeToggle,
    AppSessionConfigurationResponse,
    LanguageOption,
    ModelConfigurationResponse,
    EmergencySupportConfigurationResponse,
    OnboardingPolicyConfigurationResponse,
    OnboardingTextConfigurationResponse,
    OnboardingTextScreenConfig,
    PromptTemplateItem,
    PromptTemplatesResponse,
    SupportedLanguagesResponse,
    UpdateAppSessionConfigurationRequest,
    UpdateModelConfigurationRequest,
    UpdateEmergencySupportConfigurationRequest,
    UpdateOnboardingPolicyConfigurationRequest,
    UpdateOnboardingTextConfigurationRequest,
    UpdatePromptTemplatesRequest,
    UpdateSupportedLanguagesRequest,
    UserTypeToggle,
)
from app.services.app_session_service import (
    APP_SESSION_CONFIGURATION_KEY,
    load_app_session_configuration,
)
from app.services.emergency_support_service import (
    DEFAULT_EMERGENCY_SUPPORT_CONFIGURATION,
    load_emergency_support_configuration,
    save_emergency_support_configuration,
)

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
PROMPT_TEMPLATES_KEY = 'admin.prompt_templates'
MODEL_CONFIGURATION_KEY = 'admin.model_configuration'
ONBOARDING_TEXT_CONFIGURATION_KEY = 'admin.onboarding_text_configuration'
ONBOARDING_POLICY_CONFIGURATION_KEY = 'admin.onboarding_policy_configuration'
DEFAULT_PROMPT_TEMPLATES = {
    'items': [
        {
            'key': 'onboarding.first_reframe',
            'label': 'Onboarding First Reframe',
            'system_prompt': 'Generate a short reframe, one next step, and one Socratic question.',
            'developer_prompt': '',
            'enabled': True,
        },
        {
            'key': 'onboarding.goal_microcopy',
            'label': 'Onboarding Goal Microcopy',
            'system_prompt': 'Generate a one-line goal confirmation.',
            'developer_prompt': '',
            'enabled': True,
        },
        {
            'key': 'chat.default',
            'label': 'Default Chat Coach',
            'system_prompt': 'Keep the response supportive, non-clinical, and brief.',
            'developer_prompt': '',
            'enabled': True,
        },
    ]
}
DEFAULT_MODEL_CONFIGURATION = {
    'provider': 'ollama',
    'default_model': 'mistral',
    'onboarding_model': 'mistral',
    'fallback_model': 'mistral',
    'base_url': 'http://localhost:11434',
    'timeout_seconds': 60,
    'temperature': 0.2,
    'enabled': True,
}
DEFAULT_ONBOARDING_TEXT_CONFIGURATION = {
    'screens': [
        {'key': 'welcome', 'title': 'Onboarding', 'subtitle': 'Let us set up the right support for you.', 'primary_cta': 'Get started', 'secondary_cta': '', 'enabled': True},
        {'key': 'goal', 'title': 'What do you want help with?', 'subtitle': 'Choose the area you want ReframeQ to focus on first.', 'primary_cta': 'Continue', 'secondary_cta': 'Back', 'enabled': True},
        {'key': 'clarity', 'title': 'How are things feeling right now?', 'subtitle': 'This helps us adjust tone and pace.', 'primary_cta': 'Continue', 'secondary_cta': 'Back', 'enabled': True},
        {'key': 'style', 'title': 'Choose your guidance style', 'subtitle': 'Pick the tone that will feel most useful right now.', 'primary_cta': 'Continue', 'secondary_cta': 'Back', 'enabled': True},
        {'key': 'reframe', 'title': 'Your first reframe', 'subtitle': 'A calmer way to look at this thought.', 'primary_cta': 'Save and continue', 'secondary_cta': 'Edit my thought', 'enabled': True},
    ]
}
DEFAULT_ONBOARDING_POLICY_CONFIGURATION = {
    'onboarding_enabled': True,
    'allow_resume': True,
    'enabled_user_types': [
        {'key': 'adult', 'label': 'Adult', 'enabled': True},
        {'key': 'teen', 'label': 'Teen', 'enabled': True},
        {'key': 'guardian', 'label': 'Guardian', 'enabled': True},
    ],
    'enabled_account_modes': [
        {'key': 'individual', 'label': 'Individual', 'enabled': True},
        {'key': 'family_owner', 'label': 'Family Owner', 'enabled': True},
        {'key': 'family_join', 'label': 'Family Join', 'enabled': True},
    ],
    'allow_family_flows': True,
    'require_invite_for_family_join': True,
}
EMERGENCY_SUPPORT_CONFIGURATION_KEY = 'admin.emergency_support_configuration'


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


def _load_json_setting(db: Session, key: str, default: dict) -> dict:
    setting = db.execute(select(PlatformSetting).where(PlatformSetting.key == key)).scalar_one_or_none()
    if not setting:
        setting = PlatformSetting(key=key, value_json=json.dumps(default))
        db.add(setting)
        db.commit()
        db.refresh(setting)
        return default.copy()
    try:
        parsed = json.loads(setting.value_json)
        if isinstance(parsed, dict):
            merged = default.copy()
            merged.update(parsed)
            return merged
    except json.JSONDecodeError:
        pass
    return default.copy()


def _save_json_setting(db: Session, key: str, value: dict) -> dict:
    setting = db.execute(select(PlatformSetting).where(PlatformSetting.key == key)).scalar_one_or_none()
    if not setting:
        setting = PlatformSetting(key=key, value_json=json.dumps(value))
        db.add(setting)
    else:
        setting.value_json = json.dumps(value)
    db.commit()
    return value


def _serialize_emergency_support_configuration(data: dict) -> EmergencySupportConfigurationResponse:
    merged: dict = DEFAULT_EMERGENCY_SUPPORT_CONFIGURATION.copy()
    merged.update(data)
    return EmergencySupportConfigurationResponse(**merged)


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


@router.get('/prompts', response_model=PromptTemplatesResponse)
def list_prompt_templates(
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.read'))],
    db: Annotated[Session, Depends(get_db)],
) -> PromptTemplatesResponse:
    _ = current_user
    data = _load_json_setting(db, PROMPT_TEMPLATES_KEY, DEFAULT_PROMPT_TEMPLATES)
    return PromptTemplatesResponse(items=[PromptTemplateItem(**item) for item in data.get('items', [])])


@router.put('/prompts', response_model=PromptTemplatesResponse)
def update_prompt_templates(
    payload: UpdatePromptTemplatesRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.write'))],
    db: Annotated[Session, Depends(get_db)],
) -> PromptTemplatesResponse:
    data = {'items': [item.model_dump() for item in payload.items]}
    _save_json_setting(db, PROMPT_TEMPLATES_KEY, data)
    db.add(AuditLog(actor_email=current_user.get('sub', ''), action='prompt_templates_updated', module='settings', details=f'count={len(payload.items)}'))
    db.commit()
    return PromptTemplatesResponse(items=payload.items)


@router.get('/models', response_model=ModelConfigurationResponse)
def get_model_configuration(
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.read'))],
    db: Annotated[Session, Depends(get_db)],
) -> ModelConfigurationResponse:
    _ = current_user
    return ModelConfigurationResponse(**_load_json_setting(db, MODEL_CONFIGURATION_KEY, DEFAULT_MODEL_CONFIGURATION))


@router.put('/models', response_model=ModelConfigurationResponse)
def update_model_configuration(
    payload: UpdateModelConfigurationRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.write'))],
    db: Annotated[Session, Depends(get_db)],
) -> ModelConfigurationResponse:
    saved = _save_json_setting(db, MODEL_CONFIGURATION_KEY, payload.model_dump())
    db.add(AuditLog(actor_email=current_user.get('sub', ''), action='model_configuration_updated', module='settings', details=f"default_model={payload.default_model};onboarding_model={payload.onboarding_model}"))
    db.commit()
    return ModelConfigurationResponse(**saved)


@router.get('/app-session', response_model=AppSessionConfigurationResponse)
def get_app_session_configuration(
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.read'))],
    db: Annotated[Session, Depends(get_db)],
) -> AppSessionConfigurationResponse:
    _ = current_user
    return AppSessionConfigurationResponse(**load_app_session_configuration(db))


@router.put('/app-session', response_model=AppSessionConfigurationResponse)
def update_app_session_configuration(
    payload: UpdateAppSessionConfigurationRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.write'))],
    db: Annotated[Session, Depends(get_db)],
) -> AppSessionConfigurationResponse:
    saved = _save_json_setting(db, APP_SESSION_CONFIGURATION_KEY, payload.model_dump())
    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='app_session_configuration_updated',
            module='settings',
            details=f"app_session_duration_days={payload.app_session_duration_days}",
        )
    )
    db.commit()
    return AppSessionConfigurationResponse(**saved)


@router.get('/onboarding-text', response_model=OnboardingTextConfigurationResponse)
def get_onboarding_text_configuration(
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.read'))],
    db: Annotated[Session, Depends(get_db)],
) -> OnboardingTextConfigurationResponse:
    _ = current_user
    data = _load_json_setting(db, ONBOARDING_TEXT_CONFIGURATION_KEY, DEFAULT_ONBOARDING_TEXT_CONFIGURATION)
    return OnboardingTextConfigurationResponse(screens=[OnboardingTextScreenConfig(**screen) for screen in data.get('screens', [])])


@router.put('/onboarding-text', response_model=OnboardingTextConfigurationResponse)
def update_onboarding_text_configuration(
    payload: UpdateOnboardingTextConfigurationRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.write'))],
    db: Annotated[Session, Depends(get_db)],
) -> OnboardingTextConfigurationResponse:
    data = {'screens': [screen.model_dump() for screen in payload.screens]}
    _save_json_setting(db, ONBOARDING_TEXT_CONFIGURATION_KEY, data)
    db.add(AuditLog(actor_email=current_user.get('sub', ''), action='onboarding_text_updated', module='settings', details=f'screens={len(payload.screens)}'))
    db.commit()
    return OnboardingTextConfigurationResponse(screens=payload.screens)


@router.get('/onboarding-policy', response_model=OnboardingPolicyConfigurationResponse)
def get_onboarding_policy_configuration(
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.read'))],
    db: Annotated[Session, Depends(get_db)],
) -> OnboardingPolicyConfigurationResponse:
    _ = current_user
    data = _load_json_setting(db, ONBOARDING_POLICY_CONFIGURATION_KEY, DEFAULT_ONBOARDING_POLICY_CONFIGURATION)
    return OnboardingPolicyConfigurationResponse(
        onboarding_enabled=bool(data.get('onboarding_enabled', True)),
        allow_resume=bool(data.get('allow_resume', True)),
        enabled_user_types=[UserTypeToggle(**item) for item in data.get('enabled_user_types', [])],
        enabled_account_modes=[AccountModeToggle(**item) for item in data.get('enabled_account_modes', [])],
        allow_family_flows=bool(data.get('allow_family_flows', True)),
        require_invite_for_family_join=bool(data.get('require_invite_for_family_join', True)),
    )


@router.put('/onboarding-policy', response_model=OnboardingPolicyConfigurationResponse)
def update_onboarding_policy_configuration(
    payload: UpdateOnboardingPolicyConfigurationRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.write'))],
    db: Annotated[Session, Depends(get_db)],
) -> OnboardingPolicyConfigurationResponse:
    saved = _save_json_setting(db, ONBOARDING_POLICY_CONFIGURATION_KEY, payload.model_dump())
    db.add(AuditLog(actor_email=current_user.get('sub', ''), action='onboarding_policy_updated', module='settings', details=f"family_flows={payload.allow_family_flows};onboarding_enabled={payload.onboarding_enabled}"))
    db.commit()
    return OnboardingPolicyConfigurationResponse(
        onboarding_enabled=bool(saved.get('onboarding_enabled', True)),
        allow_resume=bool(saved.get('allow_resume', True)),
        enabled_user_types=[UserTypeToggle(**item) for item in saved.get('enabled_user_types', [])],
        enabled_account_modes=[AccountModeToggle(**item) for item in saved.get('enabled_account_modes', [])],
        allow_family_flows=bool(saved.get('allow_family_flows', True)),
        require_invite_for_family_join=bool(saved.get('require_invite_for_family_join', True)),
    )


@router.get('/emergency-support', response_model=EmergencySupportConfigurationResponse)
def get_emergency_support_configuration(
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.read'))],
    db: Annotated[Session, Depends(get_db)],
) -> EmergencySupportConfigurationResponse:
    _ = current_user
    return _serialize_emergency_support_configuration(load_emergency_support_configuration(db))


@router.put('/emergency-support', response_model=EmergencySupportConfigurationResponse)
def update_emergency_support_configuration(
    payload: UpdateEmergencySupportConfigurationRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('settings.write'))],
    db: Annotated[Session, Depends(get_db)],
) -> EmergencySupportConfigurationResponse:
    existing = load_emergency_support_configuration(db)
    saved = save_emergency_support_configuration(db, payload.model_dump())
    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='emergency_support_configuration_updated',
            module='settings',
            details=(
                f"enabled:{existing.get('enabled', True)}->{payload.enabled};"
                f"resources={len(payload.resources)};max_contacts={payload.trusted_contact_rules.max_contacts}"
            ),
        )
    )
    db.commit()
    return _serialize_emergency_support_configuration(saved)
