from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_app_permissions
from app.db.session import get_db
from app.models import User, UserDetail

router = APIRouter()


def _dashboard_copy(primary_goal: str, full_name: str) -> tuple[str, str]:
    goal = (primary_goal or '').strip().lower()
    name = (full_name or '').strip() or 'there'
    if goal == 'focus':
        return (f'Welcome back, {name}', 'Start with one small task and a calmer next step.')
    if goal == 'friendships':
        return (f'Welcome back, {name}', 'Use your saved reframe and one grounded social check-in today.')
    if goal == 'parenting':
        return (f'Welcome back, {name}', 'Begin with one calmer parenting reflection today.')
    return (f'Welcome back, {name}', 'Pick up where you left off with your saved onboarding support.')


@router.get('/me')
def get_my_profile(
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    email = current_user.get('sub', '')
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        return {'email': email, 'role': current_user.get('role', '')}

    detail = db.execute(select(UserDetail).where(UserDetail.user_id == user.id)).scalar_one_or_none()
    state = detail.onboarding_state if detail and isinstance(detail.onboarding_state, dict) else {}
    full_name = detail.full_name if detail and detail.full_name else ''
    primary_goal = str(state.get('primary_goal') or '')
    dashboard_title, dashboard_subtitle = _dashboard_copy(primary_goal, full_name)

    return {
        'email': user.email,
        'role': user.role,
        'full_name': full_name,
        'country': detail.country if detail else '',
        'language': detail.language if detail else 'en',
        'account_mode': state.get('account_mode', ''),
        'user_type': state.get('user_type', ''),
        'primary_goal': primary_goal,
        'coach_style': state.get('coach_style', ''),
        'dashboard_title': dashboard_title,
        'dashboard_subtitle': dashboard_subtitle,
        'onboarding': {
            'step': detail.onboarding_step if detail and detail.onboarding_step else 'welcome',
            'completed': bool(detail.onboarding_completed) if detail else False,
            'updated_at': detail.onboarding_updated_at.isoformat() if detail and detail.onboarding_updated_at else None,
            'state': state,
        },
    }
