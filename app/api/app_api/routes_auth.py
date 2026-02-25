from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import login

router = APIRouter()


@router.post('/login', response_model=TokenResponse)
def app_login(payload: LoginRequest) -> TokenResponse:
    token, role = login(payload.email, payload.password)
    if role != 'app_user':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='App credentials required')
    return TokenResponse(access_token=token, role=role)
