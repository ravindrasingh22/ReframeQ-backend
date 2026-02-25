from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_admin_permissions

router = APIRouter()


@router.get('/')
def list_users(
    current_user: Annotated[dict, Depends(require_admin_permissions('users.read_limited'))]
) -> dict:
    return {'requested_by': current_user.get('sub'), 'visibility': 'limited_metadata', 'users': []}


@router.post('/{user_id}/issues')
def resolve_user_issue(
    user_id: int,
    current_user: Annotated[dict, Depends(require_admin_permissions('users.manage_issues'))]
) -> dict:
    return {'requested_by': current_user.get('sub'), 'user_id': user_id, 'status': 'issue_updated'}
