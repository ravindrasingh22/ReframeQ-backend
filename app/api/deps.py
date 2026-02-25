from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.rbac import ADMIN_ROLES, Permission, has_permissions
from app.core.security import decode_token

app_oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/app/auth/login')
admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/admin/auth/login')


def _decode_or_401(token: str) -> dict:
    try:
        return decode_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired token'
        ) from exc


def get_current_app_user(token: Annotated[str, Depends(app_oauth2_scheme)]) -> dict:
    payload = _decode_or_401(token)
    if payload.get('role') != 'app_user':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='App user role required')
    return payload


def get_current_admin_actor(token: Annotated[str, Depends(admin_oauth2_scheme)]) -> dict:
    payload = _decode_or_401(token)
    if payload.get('role') not in ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin console role required')
    return payload


def require_admin_permissions(*required_permissions: Permission) -> Callable:
    def dependency(current_user: Annotated[dict, Depends(get_current_admin_actor)]) -> dict:
        role = str(current_user.get('role', ''))
        if not has_permissions(role, required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Missing permissions: {", ".join(required_permissions)}'
            )
        return current_user

    return dependency


def require_app_permissions(*required_permissions: Permission) -> Callable:
    def dependency(current_user: Annotated[dict, Depends(get_current_app_user)]) -> dict:
        role = str(current_user.get('role', ''))
        if not has_permissions(role, required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Missing permissions: {", ".join(required_permissions)}'
            )
        return current_user

    return dependency
