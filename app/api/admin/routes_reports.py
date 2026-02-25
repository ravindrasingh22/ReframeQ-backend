from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_admin_permissions

router = APIRouter()


@router.get('/overview')
def reports_overview(
    current_user: Annotated[dict, Depends(require_admin_permissions('analytics.read'))]
) -> dict:
    return {
        'requested_by': current_user.get('sub'),
        'summary': {
            'dau': 0,
            'journey_completion_rate': 0,
            'sensitive_content_detections': 0
        }
    }
