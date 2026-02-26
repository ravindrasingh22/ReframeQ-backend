from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_actor
from app.db.session import get_db
from app.models import User, UserDetail
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import is_admin_console_role, login

router = APIRouter()


def _name_from_email(email: str) -> str:
    local = email.split('@')[0].replace('.', ' ').replace('_', ' ').replace('-', ' ')
    return (' '.join(local.split())).title() or email


@router.post('/login', response_model=TokenResponse)
def admin_login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    token, role = login(payload.email, payload.password)
    if not is_admin_console_role(role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin console credentials required')

    full_name = _name_from_email(payload.email)
    user = db.execute(select(User).where(User.email == payload.email.strip().lower())).scalar_one_or_none()
    if user:
        detail = db.execute(select(UserDetail).where(UserDetail.user_id == user.id)).scalar_one_or_none()
        if detail and detail.full_name and detail.full_name.strip():
            full_name = detail.full_name.strip()

    return TokenResponse(access_token=token, role=role, full_name=full_name)


@router.get('/me')
def admin_me(
    current_user: Annotated[dict, Depends(get_current_admin_actor)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    email = str(current_user.get('sub', '')).strip().lower()
    role = str(current_user.get('role', '')).strip().lower()

    full_name = _name_from_email(email)
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user:
        detail = db.execute(select(UserDetail).where(UserDetail.user_id == user.id)).scalar_one_or_none()
        if detail and detail.full_name and detail.full_name.strip():
            full_name = detail.full_name.strip()

    return {'email': email, 'role': role, 'full_name': full_name}
