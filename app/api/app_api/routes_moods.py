from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_app_permissions

router = APIRouter()


@router.get('/')
def list_moods(
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))]
) -> dict:
    return {'owner': current_user.get('sub'), 'items': []}
