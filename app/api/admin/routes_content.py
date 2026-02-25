from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_admin_permissions

router = APIRouter()


@router.get('/journeys')
def list_journeys(
    current_user: Annotated[dict, Depends(require_admin_permissions('content.read'))]
) -> dict:
    return {'requested_by': current_user.get('sub'), 'items': []}


@router.post('/journeys')
def create_journey(
    current_user: Annotated[dict, Depends(require_admin_permissions('content.write'))]
) -> dict:
    return {'requested_by': current_user.get('sub'), 'status': 'created'}
