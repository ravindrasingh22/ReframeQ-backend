from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin_permissions
from app.db.session import get_db
from app.models import AuditLog, User
from app.schemas.admin import AuditListResponse, AuditLogItem

router = APIRouter()


@router.get('/', response_model=AuditListResponse)
def list_audit_events(
    current_user: Annotated[dict, Depends(require_admin_permissions('audit.read'))],
    db: Annotated[Session, Depends(get_db)],
    start_date: str | None = Query(default=None, description='YYYY-MM-DD'),
    end_date: str | None = Query(default=None, description='YYYY-MM-DD'),
    actor_email: str | None = Query(default=None),
    role: str | None = Query(default=None),
    action: str | None = Query(default=None),
    window: str | None = Query(default=None, description='24h|48h|1d|7d|30d'),
) -> AuditListResponse:
    stmt: Select = select(AuditLog, User.role).outerjoin(User, func.lower(User.email) == func.lower(AuditLog.actor_email))

    if start_date:
        try:
            start = datetime.combine(date.fromisoformat(start_date), time.min).replace(tzinfo=timezone.utc)
            stmt = stmt.where(AuditLog.created_at >= start)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='start_date must be YYYY-MM-DD') from exc

    if end_date:
        try:
            end = datetime.combine(date.fromisoformat(end_date), time.min).replace(tzinfo=timezone.utc) + timedelta(days=1)
            stmt = stmt.where(AuditLog.created_at < end)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='end_date must be YYYY-MM-DD') from exc

    if actor_email:
        stmt = stmt.where(func.lower(AuditLog.actor_email).like(f"%{actor_email.strip().lower()}%"))
    if role:
        stmt = stmt.where(User.role == role.strip().lower())
    if action:
        stmt = stmt.where(func.lower(AuditLog.action).like(f"%{action.strip().lower()}%"))
    if window:
        token = window.strip().lower()
        now = datetime.now(timezone.utc)
        delta_map = {
            '24h': timedelta(hours=24),
            '48h': timedelta(hours=48),
            '1d': timedelta(days=1),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30),
        }
        if token not in delta_map:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='window must be one of 24h,48h,1d,7d,30d')
        stmt = stmt.where(AuditLog.created_at >= (now - delta_map[token]))

    rows = db.execute(stmt.order_by(AuditLog.id.desc()).limit(200)).all()
    return AuditListResponse(
        requested_by=current_user.get('sub'),
        events=[
            AuditLogItem(
                id=event.id,
                actor_email=event.actor_email,
                actor_role=actor_role,
                action=event.action,
                module=event.module,
                details=event.details,
                created_at=event.created_at.isoformat(),
            )
            for event, actor_role in rows
        ]
    )
