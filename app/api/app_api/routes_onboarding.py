import json
import secrets
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_app_permissions
from app.db.session import get_db
from app.models import PlatformSetting, User, UserDetail, UserInvite
from app.schemas.onboarding import (
    OnboardingConfigurationResponse,
    OnboardingPolicySummary,
    OnboardingScreenTextItem,
    OnboardingToggleItem,
    InviteValidationRequest,
    InviteValidationResponse,
    OnboardingSummary,
    SaveOnboardingRequest,
    SafetyScanRequest,
    SafetyScanResponse,
)

router = APIRouter()

SEVERE_KEYWORDS = ['suicide', 'kill myself', 'hurt myself', 'end my life', 'immediate danger', 'unsafe']
MODERATE_KEYWORDS = ['panic', "can't cope", 'cant cope', 'break down', 'hopeless', 'harm']
ONBOARDING_TEXT_CONFIGURATION_KEY = 'admin.onboarding_text_configuration'
ONBOARDING_POLICY_CONFIGURATION_KEY = 'admin.onboarding_policy_configuration'
DEFAULT_ONBOARDING_TEXT_CONFIGURATION = {
    'screens': [
        {'key': 'welcome', 'title': 'Onboarding', 'subtitle': 'Let us set up the right support for you.', 'primary_cta': 'Get started', 'secondary_cta': 'I have a family invite', 'enabled': True},
        {'key': 'goal', 'title': 'What do you want help with?', 'subtitle': 'Choose the area you want ReframeQ to focus on first.', 'primary_cta': 'Continue', 'secondary_cta': '', 'enabled': True},
        {'key': 'clarity', 'title': 'How are things feeling right now?', 'subtitle': 'This helps us adjust tone and pace.', 'primary_cta': 'Continue', 'secondary_cta': '', 'enabled': True},
        {'key': 'style', 'title': 'Choose your guidance style', 'subtitle': 'Pick the tone that will feel most useful right now.', 'primary_cta': 'Continue', 'secondary_cta': 'Skip', 'enabled': True},
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


def _load_json_setting(db: Session, key: str, default: dict) -> dict:
    setting = db.execute(select(PlatformSetting).where(PlatformSetting.key == key)).scalar_one_or_none()
    if not setting:
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


def _get_or_create_detail(db: Session, user_id: int) -> UserDetail:
    detail = db.execute(select(UserDetail).where(UserDetail.user_id == user_id)).scalar_one_or_none()
    if detail:
        return detail
    detail = UserDetail(user_id=user_id, full_name='', country='', language='en')
    db.add(detail)
    db.flush()
    return detail


def _ensure_invite_code(invite: UserInvite) -> str:
    if invite.invite_code and invite.invite_code.strip():
        return invite.invite_code.strip().upper()
    invite.invite_code = f'FAM-{secrets.token_hex(3).upper()}'
    return invite.invite_code


def _empty_onboarding_state(detail: UserDetail) -> dict:
    return {
        'account_mode': '',
        'invite_code': '',
        'invite_validated': False,
        'user_type': '',
        'primary_goal': '',
        'secondary_goals': [],
        'clarity': 0,
        'control': 0,
        'noise': 0,
        'readiness': 0,
        'coach_style': '',
        'first_thought': '',
        'safety_flag': 'none',
        'full_name': detail.full_name,
        'email': '',
        'reminder_preference': '',
        'child_display_name': '',
        'child_age_band': '',
        'daily_time_limit': '',
        'topic_restrictions': '',
        'visibility_rule': '',
        'guardian_consent': False,
        'onboarding_complete': detail.onboarding_completed,
        'language': detail.language,
        'country': detail.country,
        'first_reframe_snapshot': {},
    }


@router.post('/invite/validate', response_model=InviteValidationResponse)
def validate_invite(
    payload: InviteValidationRequest,
    db: Annotated[Session, Depends(get_db)],
) -> InviteValidationResponse:
    code = payload.invite_code.strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='invite_code is required')

    invite = db.execute(select(UserInvite).where(UserInvite.invite_code == code)).scalar_one_or_none()
    if not invite:
        return InviteValidationResponse(valid=False, invite_code=code, status='invalid', account_mode='family_join')

    user = db.execute(select(User).where(User.id == invite.user_id)).scalar_one_or_none()
    _ensure_invite_code(invite)
    db.commit()
    return InviteValidationResponse(
        valid=invite.status == 'invited',
        invite_code=code,
        status=invite.status,
        account_mode='family_join',
        invited_user_email=user.email if user else None,
    )


@router.get('/config', response_model=OnboardingConfigurationResponse)
def get_onboarding_configuration(
    db: Annotated[Session, Depends(get_db)],
) -> OnboardingConfigurationResponse:
    policy = _load_json_setting(db, ONBOARDING_POLICY_CONFIGURATION_KEY, DEFAULT_ONBOARDING_POLICY_CONFIGURATION)
    text = _load_json_setting(db, ONBOARDING_TEXT_CONFIGURATION_KEY, DEFAULT_ONBOARDING_TEXT_CONFIGURATION)
    return OnboardingConfigurationResponse(
        policy=OnboardingPolicySummary(
            onboarding_enabled=bool(policy.get('onboarding_enabled', True)),
            allow_resume=bool(policy.get('allow_resume', True)),
            allow_family_flows=bool(policy.get('allow_family_flows', True)),
            require_invite_for_family_join=bool(policy.get('require_invite_for_family_join', True)),
            enabled_user_types=[OnboardingToggleItem(**item) for item in policy.get('enabled_user_types', [])],
            enabled_account_modes=[OnboardingToggleItem(**item) for item in policy.get('enabled_account_modes', [])],
        ),
        text=[OnboardingScreenTextItem(**screen) for screen in text.get('screens', [])],
    )


@router.post('/safety/scan', response_model=SafetyScanResponse)
def safety_scan(payload: SafetyScanRequest) -> SafetyScanResponse:
    normalized = payload.message.strip().lower()
    if any(keyword in normalized for keyword in SEVERE_KEYWORDS):
        return SafetyScanResponse(scan_status='handoff', policy_code='severe_risk', needs_handoff=True)
    if any(keyword in normalized for keyword in MODERATE_KEYWORDS):
        return SafetyScanResponse(scan_status='limit', policy_code='elevated_distress', needs_handoff=False)
    return SafetyScanResponse(scan_status='allow', policy_code='ok', needs_handoff=False)


@router.put('/state', response_model=OnboardingSummary)
def save_onboarding_state(
    payload: SaveOnboardingRequest,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> OnboardingSummary:
    email = str(current_user.get('sub', '')).strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='App account not found')

    detail = _get_or_create_detail(db, user.id)
    detail.onboarding_step = payload.step.strip() or detail.onboarding_step or 'welcome'
    detail.onboarding_completed = payload.completed or payload.state.onboarding_complete
    detail.onboarding_state = payload.state.model_dump()
    detail.onboarding_updated_at = datetime.now(timezone.utc)
    if payload.state.full_name.strip():
        detail.full_name = payload.state.full_name.strip()
    if payload.state.country.strip():
        detail.country = payload.state.country.strip()
    if payload.state.language.strip():
        detail.language = payload.state.language.strip()

    db.commit()
    return OnboardingSummary(
        step=detail.onboarding_step,
        completed=detail.onboarding_completed,
        state=payload.state,
        updated_at=detail.onboarding_updated_at.isoformat() if detail.onboarding_updated_at else None,
    )


@router.get('/state', response_model=OnboardingSummary)
def get_onboarding_state(
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> OnboardingSummary:
    email = str(current_user.get('sub', '')).strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='App account not found')

    detail = _get_or_create_detail(db, user.id)
    state = _empty_onboarding_state(detail)
    if isinstance(detail.onboarding_state, dict):
        state.update(detail.onboarding_state)

    return OnboardingSummary(
        step=detail.onboarding_step or 'welcome',
        completed=detail.onboarding_completed,
        state=state,  # type: ignore[arg-type]
        updated_at=detail.onboarding_updated_at.isoformat() if detail.onboarding_updated_at else None,
    )
