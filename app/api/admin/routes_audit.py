from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_admin_permissions

router = APIRouter()


@router.get('/')
def list_audit_events(
    current_user: Annotated[dict, Depends(require_admin_permissions('audit.read'))]
) -> dict:
    return {'requested_by': current_user.get('sub'), 'events': []}
