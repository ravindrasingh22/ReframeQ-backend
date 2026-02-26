from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permissions
from app.db.session import get_db
from app.models import AnalyticsEvent
from app.schemas.admin import AnalyticsOverviewResponse, AnalyticsSummary

router = APIRouter()


@router.get('/overview', response_model=AnalyticsOverviewResponse)
def reports_overview(
    current_user: Annotated[dict, Depends(require_admin_permissions('analytics.read'))],
    db: Annotated[Session, Depends(get_db)]
) -> AnalyticsOverviewResponse:
    dau = db.execute(
        select(func.coalesce(func.sum(AnalyticsEvent.value), 0)).where(AnalyticsEvent.event_type == 'dau')
    ).scalar_one()
    completion = db.execute(
        select(func.coalesce(func.sum(AnalyticsEvent.value), 0)).where(
            AnalyticsEvent.event_type == 'journey_completion_rate'
        )
    ).scalar_one()
    sensitive = db.execute(
        select(func.coalesce(func.sum(AnalyticsEvent.value), 0)).where(
            AnalyticsEvent.event_type == 'sensitive_content_detection'
        )
    ).scalar_one()
    top = db.execute(
        select(AnalyticsEvent.journey_title)
        .where(AnalyticsEvent.event_type == 'top_journey')
        .order_by(AnalyticsEvent.id.desc())
        .limit(1)
    ).scalar_one_or_none()

    return AnalyticsOverviewResponse(
        requested_by=current_user.get('sub'),
        summary=AnalyticsSummary(
            dau=int(dau),
            journey_completion_rate=int(completion),
            sensitive_content_detections=int(sensitive),
            top_journey=top or 'n/a',
        )
    )
