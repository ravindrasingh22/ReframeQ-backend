from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import is_admin_console_role, login

router = APIRouter()


@router.post('/login', response_model=TokenResponse)
def admin_login(payload: LoginRequest) -> TokenResponse:
    token, role = login(payload.email, payload.password)
    if not is_admin_console_role(role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin console credentials required')
    return TokenResponse(access_token=token, role=role)
