from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_app_permissions

router = APIRouter()


@router.get('/me')
def get_my_profile(
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))]
) -> dict:
    return {'email': current_user.get('sub'), 'role': current_user.get('role')}
