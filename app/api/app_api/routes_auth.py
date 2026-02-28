from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User, UserDetail
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import login

router = APIRouter()
pwd_context = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')


def _name_from_email(email: str) -> str:
    local = email.split('@')[0].replace('.', ' ').replace('_', ' ').replace('-', ' ')
    return (' '.join(local.split())).title() or email


@router.post('/register', response_model=TokenResponse)
def app_register(payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    email = payload.email.strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Email is required')
    if len(payload.password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Password must be at least 8 characters')

    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already exists')

    full_name = payload.full_name.strip() or _name_from_email(email)
    language = payload.language.strip().lower() or 'en'

    user = User(
        email=email,
        password_hash=pwd_context.hash(payload.password),
        role='app_user',
        is_active=True,
    )
    db.add(user)
    db.flush()

    db.add(
        UserDetail(
            user_id=user.id,
            full_name=full_name,
            country=payload.country.strip(),
            language=language,
        )
    )
    db.commit()

    token, role = login(email, payload.password)
    return TokenResponse(access_token=token, role=role, full_name=full_name)


@router.post('/login', response_model=TokenResponse)
def app_login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    token, role = login(payload.email, payload.password)
    if role != 'app_user':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='App credentials required')

    email = payload.email.strip().lower()
    full_name = _name_from_email(email)

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user:
        detail = db.execute(select(UserDetail).where(UserDetail.user_id == user.id)).scalar_one_or_none()
        if detail and detail.full_name and detail.full_name.strip():
            full_name = detail.full_name.strip()

    return TokenResponse(access_token=token, role=role, full_name=full_name)
