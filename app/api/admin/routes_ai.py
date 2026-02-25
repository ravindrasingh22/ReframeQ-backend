from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_admin_permissions

router = APIRouter()


@router.get('/prompts')
def list_prompt_templates(
    current_user: Annotated[dict, Depends(require_admin_permissions('ai.read'))]
) -> dict:
    return {'requested_by': current_user.get('sub'), 'templates': []}


@router.post('/routing-rules')
def update_routing_rules(
    current_user: Annotated[dict, Depends(require_admin_permissions('ai.write'))]
) -> dict:
    return {'requested_by': current_user.get('sub'), 'status': 'updated'}
