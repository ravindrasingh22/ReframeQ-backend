from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.admin.routes_settings import get_supported_languages
from app.api.deps import require_app_permissions
from app.db.session import get_db
from app.models import AuditLog, User, UserDetail
from app.schemas.onboarding import AppProfileResponse, ChangeAppPasswordRequest, UpdateAppProfileRequest

router = APIRouter()
pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')
LANGUAGE_ALIASES = {
    'english': 'en',
    'spanish': 'es',
    'french': 'fr',
    'german': 'de',
    'italian': 'it',
    'portuguese': 'pt',
    'hindi': 'hi',
    'arabic': 'ar',
    'japanese': 'ja',
    'korean': 'ko',
    'chinese': 'zh',
    'russian': 'ru',
    'turkish': 'tr',
    'dutch': 'nl',
    'swedish': 'sv',
    'bengali': 'bn',
    'urdu': 'ur',
    'tamil': 'ta',
    'telugu': 'te',
    'marathi': 'mr',
}


def _dashboard_copy(primary_goal: str, full_name: str) -> tuple[str, str]:
    goal = (primary_goal or '').strip().lower()
    name = (full_name or '').strip() or 'there'
    if goal == 'focus':
        return (f'Welcome back, {name}', 'Start with one small task and a calmer next step.')
    if goal == 'friendships':
        return (f'Welcome back, {name}', 'Use your saved reframe and one grounded social check-in today.')
    if goal == 'parenting':
        return (f'Welcome back, {name}', 'Begin with one calmer parenting reflection today.')
    return (f'Welcome back, {name}', 'Pick up where you left off with your saved onboarding support.')


def _normalize_language(value: str | None) -> str:
    raw = (value or '').strip().lower()
    if not raw:
        return 'en'
    return LANGUAGE_ALIASES.get(raw, raw)


def _coerce_supported_language(value: str | None, supported_languages: list[str]) -> str:
    normalized_supported = [str(v).strip().lower() for v in supported_languages if str(v).strip()]
    normalized = _normalize_language(value)
    if normalized in normalized_supported:
        return normalized
    if 'en' in normalized_supported:
        return 'en'
    return normalized_supported[0] if normalized_supported else 'en'


def _get_or_create_user_detail(db: Session, user_id: int) -> UserDetail:
    detail = db.execute(select(UserDetail).where(UserDetail.user_id == user_id)).scalar_one_or_none()
    if detail:
        return detail
    detail = UserDetail(
        user_id=user_id,
        full_name='',
        mobile_country_code='',
        mobile_number='',
        city='',
        state='',
        country='',
        language='en',
    )
    db.add(detail)
    db.flush()
    return detail


def _build_profile_response(user: User, detail: UserDetail | None) -> AppProfileResponse:
    state = detail.onboarding_state if detail and isinstance(detail.onboarding_state, dict) else {}
    full_name = detail.full_name if detail and detail.full_name else ''
    primary_goal = str(state.get('primary_goal') or '')
    dashboard_title, dashboard_subtitle = _dashboard_copy(primary_goal, full_name)

    return AppProfileResponse(
        email=user.email,
        role=user.role,
        full_name=full_name,
        mobile_country_code=detail.mobile_country_code if detail else '',
        mobile_number=detail.mobile_number if detail else '',
        city=detail.city if detail else '',
        state=detail.state if detail else '',
        country=detail.country if detail else '',
        language=detail.language if detail else 'en',
        account_mode=state.get('account_mode', ''),
        user_type=state.get('user_type', ''),
        primary_goal=primary_goal,
        coach_style=state.get('coach_style', ''),
        dashboard_title=dashboard_title,
        dashboard_subtitle=dashboard_subtitle,
        onboarding={
            'step': detail.onboarding_step if detail and detail.onboarding_step else 'welcome',
            'completed': bool(detail.onboarding_completed) if detail else False,
            'updated_at': detail.onboarding_updated_at.isoformat() if detail and detail.onboarding_updated_at else None,
            'state': state,
        },
    )


@router.get('/me', response_model=AppProfileResponse)
def get_my_profile(
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> AppProfileResponse:
    email = current_user.get('sub', '')
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        return AppProfileResponse(
            email=email,
            role=current_user.get('role', ''),
            full_name='',
            mobile_country_code='',
            mobile_number='',
            city='',
            state='',
            country='',
            language='en',
            account_mode='',
            user_type='',
            primary_goal='',
            coach_style='',
            dashboard_title='Welcome back',
            dashboard_subtitle='Pick up where you left off with your saved onboarding support.',
            onboarding={'step': 'welcome', 'completed': False, 'updated_at': None, 'state': {}},
        )

    detail = db.execute(select(UserDetail).where(UserDetail.user_id == user.id)).scalar_one_or_none()
    return _build_profile_response(user, detail)


@router.patch('/me', response_model=AppProfileResponse)
def update_my_profile(
    payload: UpdateAppProfileRequest,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> AppProfileResponse:
    email = current_user.get('sub', '')
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    detail = _get_or_create_user_detail(db, user.id)
    if payload.full_name is not None:
        detail.full_name = payload.full_name.strip()
    if payload.mobile_country_code is not None:
        detail.mobile_country_code = payload.mobile_country_code.strip()
    if payload.mobile_number is not None:
        detail.mobile_number = payload.mobile_number.strip()
    if payload.city is not None:
        detail.city = payload.city.strip()
    if payload.state is not None:
        detail.state = payload.state.strip()
    if payload.country is not None:
        detail.country = payload.country.strip()
    if payload.language is not None:
        detail.language = _coerce_supported_language(payload.language, get_supported_languages(db))

    db.add(
        AuditLog(
            actor_email=email,
            action='app_profile_updated',
            module='app-profile',
            details=(
                f'user_id={user.id};full_name={detail.full_name};mobile_country_code={detail.mobile_country_code};'
                f'mobile_number={detail.mobile_number};city={detail.city};state={detail.state};'
                f'country={detail.country};language={detail.language}'
            ),
        )
    )
    db.commit()
    db.refresh(user)
    db.refresh(detail)
    return _build_profile_response(user, detail)


@router.post('/me/password')
def change_my_password(
    payload: ChangeAppPasswordRequest,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    email = current_user.get('sub', '')
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Password must be at least 8 characters')

    user.password_hash = pwd_context.hash(payload.new_password)
    db.add(
        AuditLog(
            actor_email=email,
            action='app_password_changed',
            module='app-profile',
            details=f'user_id={user.id}',
        )
    )
    db.commit()
    return {'requested_by': email, 'user_id': user.id, 'status': 'password_updated'}
