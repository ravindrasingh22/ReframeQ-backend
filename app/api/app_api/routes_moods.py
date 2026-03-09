from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_app_permissions
from app.api.app_api.routes_dashboard import MOOD_OPTIONS, build_home_dashboard, build_mood_report_payload, get_current_account
from app.db.session import get_db
from app.models import MoodCheckin
from app.schemas.moods import MoodCheckinRequest, MoodCheckinResponse, MoodCheckinSummary, MoodReportResponse

router = APIRouter()


@router.get('/today', response_model=MoodCheckinSummary | None)
def get_today_mood(
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> MoodCheckinSummary | None:
    user, _, _, _, _ = get_current_account(db, current_user)
    today = datetime.now(timezone.utc).date()
    mood = db.execute(
        select(MoodCheckin).where(MoodCheckin.user_id == user.id, MoodCheckin.checkin_date == today)
    ).scalar_one_or_none()
    if not mood:
        return None
    return MoodCheckinSummary(mood_id=mood.mood_id, mood_label=mood.mood_label, selected_at=mood.updated_at.isoformat())


@router.post('/check-in', response_model=MoodCheckinResponse)
def save_checkin(
    payload: MoodCheckinRequest,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> MoodCheckinResponse:
    selected = next((option for option in MOOD_OPTIONS if option.id == payload.mood_id), None)
    if not selected:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid mood selection')

    user, _, _, _, _ = get_current_account(db, current_user)
    today = datetime.now(timezone.utc).date()
    mood = db.execute(
        select(MoodCheckin).where(MoodCheckin.user_id == user.id, MoodCheckin.checkin_date == today)
    ).scalar_one_or_none()
    if mood:
        mood.mood_id = selected.id
        mood.mood_label = selected.label
    else:
        mood = MoodCheckin(user_id=user.id, mood_id=selected.id, mood_label=selected.label, checkin_date=today)
        db.add(mood)

    db.commit()
    db.refresh(mood)
    dashboard = build_home_dashboard(db, current_user)
    return MoodCheckinResponse(
        checkin=MoodCheckinSummary(mood_id=mood.mood_id, mood_label=mood.mood_label, selected_at=mood.updated_at.isoformat()),
        stats=dashboard.stats,
    )


@router.get('/report', response_model=MoodReportResponse)
def get_mood_report(
    range_days: int = 30,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> MoodReportResponse:
    if range_days not in {7, 14, 30}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='range_days must be one of 7, 14, or 30')

    user, _, _, _, _ = get_current_account(db, current_user)
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=range_days - 1)
    checkins = (
        db.execute(
            select(MoodCheckin)
            .where(MoodCheckin.user_id == user.id, MoodCheckin.checkin_date >= start_date, MoodCheckin.checkin_date <= today)
            .order_by(MoodCheckin.checkin_date.asc(), MoodCheckin.id.asc())
        )
        .scalars()
        .all()
    )
    return MoodReportResponse(**build_mood_report_payload(checkins, range_days))
