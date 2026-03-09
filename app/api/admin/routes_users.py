from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permissions
from app.api.admin.routes_settings import get_supported_languages
from app.db.session import get_db
from app.models import AuditLog, MoodCheckin, User, UserDetail, UserInvite
from app.schemas.admin import (
    BulkUserActionRequest,
    ChangePasswordRequest,
    CreateUserRequest,
    UpdateUserProfileRequest,
    UpdateUserRequest,
    UserListItem,
    UserProfileResponse,
    UsersListResponse,
)

router = APIRouter()
# Use pbkdf2_sha256 to avoid bcrypt backend/version issues in container images.
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
    detail = UserDetail(user_id=user_id, full_name='', country='', language='en')
    db.add(detail)
    db.flush()
    return detail


def _user_invite(db: Session, user_id: int) -> UserInvite | None:
    return db.execute(select(UserInvite).where(UserInvite.user_id == user_id)).scalar_one_or_none()


def _ensure_invite_code(invite: UserInvite | None, user_id: int) -> str | None:
    if not invite:
        return None
    if invite.invite_code:
        return invite.invite_code
    invite.invite_code = f'FAM-{user_id:04d}'
    return invite.invite_code


def _account_state(db: Session, user: User) -> str:
    invite = _user_invite(db, user.id)
    if invite and invite.status == 'invited':
        return 'invited'
    return 'active' if user.is_active else 'paused'


def _member_since(user: User, invite: UserInvite | None) -> str | None:
    dt = invite.invited_at if invite else user.created_at
    return dt.isoformat() if dt else None


def _default_full_name_from_email(email: str) -> str:
    local = email.split('@')[0].replace('.', ' ').replace('_', ' ').replace('-', ' ')
    normalized = ' '.join(part for part in local.split() if part)
    return normalized.title() if normalized else email


def _resolved_full_name(db: Session, user: User, detail: UserDetail) -> str:
    if detail.full_name and detail.full_name.strip():
        return detail.full_name.strip()
    fallback = _default_full_name_from_email(user.email)
    detail.full_name = fallback
    db.add(detail)
    return fallback


@router.get('/', response_model=UsersListResponse)
def list_users(
    current_user: Annotated[dict, Depends(require_admin_permissions('users.read_limited'))],
    db: Annotated[Session, Depends(get_db)],
) -> UsersListResponse:
    users = db.execute(select(User).order_by(User.id.asc())).scalars().all()
    return UsersListResponse(
        requested_by=current_user.get('sub', ''),
        visibility='limited_metadata',
        users=[
            UserListItem(
                id=user.id,
                email=user.email,
                full_name=_resolved_full_name(db, user, _get_or_create_user_detail(db, user.id)),
                role=user.role,
                is_active=user.is_active,
                account_state=_account_state(db, user),
                member_since=_member_since(user, _user_invite(db, user.id)),
            )
            for user in users
        ],
    )


@router.post('/', response_model=UserListItem)
def create_user(
    payload: CreateUserRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('users.manage_issues'))],
    db: Annotated[Session, Depends(get_db)],
) -> UserListItem:
    normalized_email = payload.email.strip().lower()
    existing = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already exists')

    supported_languages = get_supported_languages(db)
    requested_language = _coerce_supported_language(payload.language, supported_languages)

    user = User(
        email=normalized_email,
        password_hash=pwd_context.hash(payload.temp_password if payload.temp_password else 'change-me'),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()

    db.add(
        UserDetail(
            user_id=user.id,
            full_name=payload.full_name.strip(),
            country=payload.country.strip(),
            language=requested_language,
        )
    )
    db.add(UserInvite(user_id=user.id, status='invited'))
    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='user_created',
            module='users',
            details=f'user_id={user.id};email={user.email};role={user.role};is_active={user.is_active}',
        )
    )
    db.commit()
    db.refresh(user)
    invite = _user_invite(db, user.id)
    _ensure_invite_code(invite, user.id)
    db.commit()
    return UserListItem(
        id=user.id,
        email=user.email,
        full_name=payload.full_name.strip(),
        role=user.role,
        is_active=user.is_active,
        account_state='invited',
        member_since=_member_since(user, _user_invite(db, user.id)),
    )


@router.get('/{user_id}/profile', response_model=UserProfileResponse)
def get_user_profile(
    user_id: int,
    current_user: Annotated[dict, Depends(require_admin_permissions('users.read_limited'))],
    db: Annotated[Session, Depends(get_db)],
) -> UserProfileResponse:
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    detail = _get_or_create_user_detail(db, user_id)
    if detail.language:
        detail.language = _normalize_language(detail.language)
    full_name = _resolved_full_name(db, user, detail)
    invite = _user_invite(db, user.id)
    invite_code = _ensure_invite_code(invite, user.id)
    mood_logs = db.execute(
        select(MoodCheckin).where(MoodCheckin.user_id == user.id).order_by(MoodCheckin.checkin_date.desc(), MoodCheckin.id.desc()).limit(30)
    ).scalars().all()
    db.commit()
    return UserProfileResponse(
        user_id=user.id,
        email=user.email,
        full_name=full_name,
        role=user.role,
        is_active=user.is_active,
        country=detail.country,
        language=_normalize_language(detail.language),
        member_since=_member_since(user, _user_invite(db, user.id)),
        invite_code=invite_code,
        onboarding_step=detail.onboarding_step,
        onboarding_completed=detail.onboarding_completed,
        onboarding_updated_at=detail.onboarding_updated_at.isoformat() if detail.onboarding_updated_at else None,
        onboarding_state=detail.onboarding_state or {},
        mood_logs=[
            {
                'id': item.id,
                'mood_id': item.mood_id,
                'mood_label': item.mood_label,
                'checkin_date': item.checkin_date.isoformat(),
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
            }
            for item in mood_logs
        ],
    )


@router.patch('/{user_id}/profile', response_model=UserProfileResponse)
def update_user_profile(
    user_id: int,
    payload: UpdateUserProfileRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('users.manage_issues'))],
    db: Annotated[Session, Depends(get_db)],
) -> UserProfileResponse:
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    detail = _get_or_create_user_detail(db, user_id)

    if payload.full_name is not None:
        detail.full_name = payload.full_name.strip()
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.country is not None:
        detail.country = payload.country.strip()
    if payload.language is not None:
        supported_languages = get_supported_languages(db)
        requested_language = _coerce_supported_language(payload.language, supported_languages)
        detail.language = requested_language

    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='user_profile_updated',
            module='users',
            details=(
                f'user_id={user_id};role={user.role};is_active={user.is_active};'
                f'full_name={detail.full_name};country={detail.country};language={detail.language}'
            ),
        )
    )
    db.commit()
    invite = _user_invite(db, user.id)
    return UserProfileResponse(
        user_id=user.id,
        email=user.email,
        full_name=_resolved_full_name(db, user, detail),
        role=user.role,
        is_active=user.is_active,
        country=detail.country,
        language=detail.language,
        member_since=_member_since(user, _user_invite(db, user.id)),
        invite_code=_ensure_invite_code(invite, user.id),
        onboarding_step=detail.onboarding_step,
        onboarding_completed=detail.onboarding_completed,
        onboarding_updated_at=detail.onboarding_updated_at.isoformat() if detail.onboarding_updated_at else None,
        onboarding_state=detail.onboarding_state or {},
    )


@router.post('/{user_id}/password')
def change_user_password(
    user_id: int,
    payload: ChangePasswordRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('users.manage_issues'))],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Password must be at least 8 characters')

    user.password_hash = pwd_context.hash(payload.new_password)
    invite = db.execute(select(UserInvite).where(UserInvite.user_id == user_id)).scalar_one_or_none()
    if invite and invite.status == 'invited':
        invite.status = 'accepted'

    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='user_password_changed',
            module='users',
            details=f'user_id={user_id}',
        )
    )
    db.commit()
    return {'requested_by': current_user.get('sub', ''), 'user_id': user_id, 'status': 'password_updated'}


@router.patch('/{user_id}', response_model=UserListItem)
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('users.manage_issues'))],
    db: Annotated[Session, Depends(get_db)],
) -> UserListItem:
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='user_updated',
            module='users',
            details=f'user_id={user_id};role={user.role};is_active={user.is_active}',
        )
    )
    db.commit()
    db.refresh(user)
    detail = _get_or_create_user_detail(db, user.id)
    return UserListItem(
        id=user.id,
        email=user.email,
        full_name=_resolved_full_name(db, user, detail),
        role=user.role,
        is_active=user.is_active,
        account_state=_account_state(db, user),
        member_since=_member_since(user, _user_invite(db, user.id)),
    )


@router.patch('/{user_id}/status', response_model=UserListItem)
def update_user_status(
    user_id: int,
    payload: UpdateUserRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('users.manage_issues'))],
    db: Annotated[Session, Depends(get_db)],
) -> UserListItem:
    if payload.is_active is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='is_active is required')
    return update_user(user_id=user_id, payload=payload, current_user=current_user, db=db)


@router.delete('/{user_id}')
def delete_user(
    user_id: int,
    current_user: Annotated[dict, Depends(require_admin_permissions('users.manage_issues'))],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    detail = db.execute(select(UserDetail).where(UserDetail.user_id == user_id)).scalar_one_or_none()
    invite = db.execute(select(UserInvite).where(UserInvite.user_id == user_id)).scalar_one_or_none()
    user_email = user.email
    if detail:
        db.delete(detail)
    if invite:
        db.delete(invite)
    db.delete(user)
    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='user_deleted',
            module='users',
            details=f'user_id={user_id};email={user_email}',
        )
    )
    db.commit()
    return {'requested_by': current_user.get('sub', ''), 'user_id': user_id, 'status': 'deleted'}


@router.post('/{user_id}/issues')
def resolve_user_issue(
    user_id: int,
    current_user: Annotated[dict, Depends(require_admin_permissions('users.manage_issues'))],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='support_issue_updated',
            module='users',
            details=f'Issue updated for user_id={user_id}',
        )
    )
    db.commit()
    return {'requested_by': current_user.get('sub', ''), 'user_id': user_id, 'status': 'issue_updated'}


@router.post('/bulk')
def bulk_user_action(
    payload: BulkUserActionRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('users.manage_issues'))],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    if not payload.user_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='user_ids is required')

    users = db.execute(select(User).where(User.id.in_(payload.user_ids))).scalars().all()
    found_ids = {u.id for u in users}
    missing = [uid for uid in payload.user_ids if uid not in found_ids]
    if missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Users not found: {missing}')

    affected = 0
    if payload.action == 'set_status':
        if payload.is_active is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='is_active is required for set_status')
        for user in users:
            user.is_active = payload.is_active
            affected += 1
    elif payload.action == 'set_role':
        if not payload.role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='role is required for set_role')
        for user in users:
            user.role = payload.role
            affected += 1
    elif payload.action == 'delete':
        for user in users:
            detail = db.execute(select(UserDetail).where(UserDetail.user_id == user.id)).scalar_one_or_none()
            invite = db.execute(select(UserInvite).where(UserInvite.user_id == user.id)).scalar_one_or_none()
            if detail:
                db.delete(detail)
            if invite:
                db.delete(invite)
            db.delete(user)
            affected += 1
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported action')

    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='users_bulk_action',
            module='users',
            details=f'action={payload.action};count={affected};ids={payload.user_ids}',
        )
    )
    db.commit()
    return {'requested_by': current_user.get('sub', ''), 'action': payload.action, 'affected': affected}
