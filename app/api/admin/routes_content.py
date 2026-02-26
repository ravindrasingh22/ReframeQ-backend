from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permissions
from app.db.session import get_db
from app.models import AuditLog, Journey
from app.schemas.admin import JourneyCreateRequest, JourneyItem, JourneyListResponse

router = APIRouter()


@router.get('/journeys', response_model=JourneyListResponse)
def list_journeys(
    current_user: Annotated[dict, Depends(require_admin_permissions('content.read'))],
    db: Annotated[Session, Depends(get_db)]
) -> JourneyListResponse:
    journeys = db.execute(select(Journey).order_by(Journey.id.asc())).scalars().all()
    return JourneyListResponse(
        requested_by=current_user.get('sub'),
        items=[
            JourneyItem(
                id=journey.id,
                title=journey.title,
                topic=journey.topic,
                difficulty=journey.difficulty,
                is_published=journey.is_published,
                summary=journey.summary,
            )
            for journey in journeys
        ]
    )


@router.post('/journeys', response_model=JourneyItem)
def create_journey(
    payload: JourneyCreateRequest,
    current_user: Annotated[dict, Depends(require_admin_permissions('content.write'))],
    db: Annotated[Session, Depends(get_db)]
) -> JourneyItem:
    journey = Journey(
        title=payload.title,
        topic=payload.topic,
        difficulty=payload.difficulty,
        summary=payload.summary,
        is_published=payload.is_published,
    )
    db.add(journey)

    log = AuditLog(
        actor_email=current_user.get('sub', ''),
        action='journey_created',
        module='content',
        details=f'Journey title={payload.title}'
    )
    db.add(log)
    db.commit()
    db.refresh(journey)

    return JourneyItem(
        id=journey.id,
        title=journey.title,
        topic=journey.topic,
        difficulty=journey.difficulty,
        is_published=journey.is_published,
        summary=journey.summary,
    )
