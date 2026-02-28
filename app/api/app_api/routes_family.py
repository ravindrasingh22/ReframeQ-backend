import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_app_permissions
from app.db.session import get_db
from app.models import AuditLog, GuardianLink, Profile, User
from app.schemas.family import (
    CreateFamilyProfileRequest,
    FamilyProfileItem,
    FamilyProfilesResponse,
    RecordGuardianConsentRequest,
    UpdateChildProfileRequest,
    UpdateChildStatusRequest,
)

router = APIRouter()


def _parse_topic_restrictions(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return []


def _build_profile_item(profile: Profile, guardian_link: GuardianLink | None = None) -> FamilyProfileItem:
    return FamilyProfileItem(
        profile_id=profile.id,
        primary_user_id=profile.user_id,
        profile_type=profile.profile_type,
        display_name=profile.display_name,
        age_band=profile.age_band,
        profile_active=profile.is_active,
        consent_granted=guardian_link.consent_granted if guardian_link else None,
        consent_text_version=guardian_link.consent_text_version if guardian_link else None,
        daily_time_limit_minutes=guardian_link.daily_time_limit_minutes if guardian_link else None,
        topic_restrictions=_parse_topic_restrictions(guardian_link.topic_restrictions_json) if guardian_link else [],
        conversation_visibility_rule=guardian_link.conversation_visibility_rule if guardian_link else None,
    )


def _get_current_account(db: Session, current_user: dict) -> User:
    email = str(current_user.get('sub', '')).strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='App account not found')
    return user


def _get_owned_profile_with_link(
    db: Session,
    current_user: dict,
    profile_id: int,
    child_only: bool = False,
) -> tuple[Profile, GuardianLink | None]:
    account = _get_current_account(db, current_user)
    profile = db.execute(select(Profile).where(Profile.id == profile_id, Profile.user_id == account.id)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Profile not found')

    if child_only and profile.profile_type != 'child':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Operation allowed only for child profiles')

    link = None
    if profile.profile_type == 'child':
        link = db.execute(select(GuardianLink).where(GuardianLink.child_profile_id == profile.id)).scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Child guardian link not found')
        if link.guardian_user_id != account.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed for this child profile')
    return profile, link


@router.get('/profiles', response_model=FamilyProfilesResponse)
def list_my_profiles(
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> FamilyProfilesResponse:
    account = _get_current_account(db, current_user)
    profiles = db.execute(select(Profile).where(Profile.user_id == account.id).order_by(Profile.id.asc())).scalars().all()
    child_ids = [p.id for p in profiles if p.profile_type == 'child']
    links_by_profile_id: dict[int, GuardianLink] = {}
    if child_ids:
        links = db.execute(select(GuardianLink).where(GuardianLink.child_profile_id.in_(child_ids))).scalars().all()
        links_by_profile_id = {link.child_profile_id: link for link in links}

    items = [_build_profile_item(profile, links_by_profile_id.get(profile.id)) for profile in profiles]
    return FamilyProfilesResponse(
        requested_by=current_user.get('sub', ''),
        primary_user_id=account.id,
        items=items,
    )


@router.post('/profiles', response_model=FamilyProfileItem)
def create_my_profile(
    payload: CreateFamilyProfileRequest,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> FamilyProfileItem:
    account = _get_current_account(db, current_user)
    if payload.profile_type not in {'child', 'adult'}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='profile_type must be child or adult')

    profile = Profile(
        user_id=account.id,
        profile_type=payload.profile_type,
        display_name=payload.display_name,
        age_band=payload.age_band,
        is_active=False if payload.profile_type == 'child' else True,
    )
    db.add(profile)
    db.flush()

    guardian_link: GuardianLink | None = None
    if payload.profile_type == 'child':
        guardian_link = GuardianLink(
            guardian_user_id=account.id,
            child_profile_id=profile.id,
            consent_granted=False,
            consent_text_version='pending',
            daily_time_limit_minutes=payload.daily_time_limit_minutes,
            topic_restrictions_json=json.dumps(payload.topic_restrictions),
            conversation_visibility_rule=payload.conversation_visibility_rule,
        )
        db.add(guardian_link)

    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='app_family_profile_created',
            module='family',
            details=f'primary_user_id={account.id};profile_id={profile.id};profile_type={payload.profile_type}',
        )
    )
    db.commit()
    return _build_profile_item(profile, guardian_link)


@router.patch('/profiles/{profile_id}', response_model=FamilyProfileItem)
def update_my_child_profile(
    profile_id: int,
    payload: UpdateChildProfileRequest,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> FamilyProfileItem:
    profile, link = _get_owned_profile_with_link(db, current_user, profile_id, child_only=True)
    assert link is not None

    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.age_band is not None:
        profile.age_band = payload.age_band
    if payload.daily_time_limit_minutes is not None:
        link.daily_time_limit_minutes = payload.daily_time_limit_minutes
    if payload.topic_restrictions is not None:
        link.topic_restrictions_json = json.dumps(payload.topic_restrictions)
    if payload.conversation_visibility_rule is not None:
        link.conversation_visibility_rule = payload.conversation_visibility_rule

    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='app_child_profile_updated',
            module='family',
            details=f'profile_id={profile_id}',
        )
    )
    db.commit()
    return _build_profile_item(profile, link)


@router.patch('/profiles/{profile_id}/status', response_model=FamilyProfileItem)
def update_my_child_status(
    profile_id: int,
    payload: UpdateChildStatusRequest,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> FamilyProfileItem:
    profile, link = _get_owned_profile_with_link(db, current_user, profile_id, child_only=True)
    profile.is_active = payload.profile_active
    assert link is not None

    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='app_child_profile_status_updated',
            module='family',
            details=f'profile_id={profile_id};is_active={payload.profile_active}',
        )
    )
    db.commit()
    return _build_profile_item(profile, link)


@router.post('/profiles/{profile_id}/consent', response_model=FamilyProfileItem)
def record_my_child_consent(
    profile_id: int,
    payload: RecordGuardianConsentRequest,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> FamilyProfileItem:
    profile, link = _get_owned_profile_with_link(db, current_user, profile_id, child_only=True)
    account = _get_current_account(db, current_user)
    assert link is not None

    if payload.guardian_user_id != account.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='guardian_user_id must match current user')

    link.consent_granted = True
    link.consent_text_version = payload.consent_text_version
    link.consented_at = datetime.now(timezone.utc)
    profile.is_active = True

    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='app_guardian_consent_recorded',
            module='family',
            details=f'profile_id={profile_id};consent_text_version={payload.consent_text_version}',
        )
    )
    db.commit()
    return _build_profile_item(profile, link)


@router.delete('/profiles/{profile_id}')
def delete_my_profile(
    profile_id: int,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    profile, link = _get_owned_profile_with_link(db, current_user, profile_id, child_only=False)
    if link:
        db.delete(link)
    db.delete(profile)
    db.add(
        AuditLog(
            actor_email=current_user.get('sub', ''),
            action='app_family_profile_deleted',
            module='family',
            details=f'profile_id={profile_id}',
        )
    )
    db.commit()
    return {'requested_by': current_user.get('sub', ''), 'profile_id': profile_id, 'status': 'deleted'}
