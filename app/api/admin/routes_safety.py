from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_admin_permissions

router = APIRouter()


@router.get('/rules')
def list_safety_rules(
    current_user: Annotated[dict, Depends(require_admin_permissions('safety.read'))]
) -> dict:
    return {'requested_by': current_user.get('sub'), 'rules': []}


@router.post('/templates')
def update_safety_templates(
    current_user: Annotated[dict, Depends(require_admin_permissions('safety.write'))]
) -> dict:
    return {'requested_by': current_user.get('sub'), 'status': 'updated'}
