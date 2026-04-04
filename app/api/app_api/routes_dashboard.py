from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.api.deps import require_app_permissions
from app.db.session import get_db
from app.models import ChatMessage, ChatThread, MoodCheckin, User, UserDetail
from app.schemas.dashboard import (
    DashboardFocusCard,
    DashboardHeader,
    DashboardStatCard,
    HomeDashboardResponse,
    MoodCheckSection,
    MoodOption,
    MoodTrendPoint,
    MoodTrendPreview,
    MoodTrendSummary,
    SuggestedToolCard,
)
from app.services.mood_reporting import build_trend_summary_data, describe_mood_pattern

router = APIRouter()

MOOD_OPTIONS = [
    MoodOption(id='overwhelmed', label='Overwhelmed', emoji='😣'),
    MoodOption(id='confused', label='Confused', emoji='😕'),
    MoodOption(id='okay', label='Okay', emoji='😐'),
    MoodOption(id='better', label='Better', emoji='🙂'),
    MoodOption(id='calm', label='Calm', emoji='😌'),
]

TOOLS = [
    SuggestedToolCard(
        id='thought-reframe',
        title='Thought Reframe',
        description='Turn one difficult thought into a more balanced view.',
        icon='brain',
        tint='#7c3aed',
        tint_bg='#ede9fe',
    ),
    SuggestedToolCard(
        id='question-builder',
        title='Question Builder',
        description='Use guided questions to challenge assumptions.',
        icon='compass',
        tint='#d946ef',
        tint_bg='#fae8ff',
    ),
    SuggestedToolCard(
        id='mood-journal',
        title='Mood Journal',
        description='Track feelings, triggers, and wins.',
        icon='book',
        tint='#0f766e',
        tint_bg='#ccfbf1',
    ),
    SuggestedToolCard(
        id='behavior-experiment',
        title='Behavior Experiment',
        description='Test a belief with one small real-world action.',
        icon='footprints',
        tint='#2563eb',
        tint_bg='#dbeafe',
    ),
    SuggestedToolCard(
        id='breathing-reset',
        title='Breathing Reset',
        description='A 2-minute guided calm-down exercise.',
        icon='play',
        tint='#c026d3',
        tint_bg='#fae8ff',
    ),
    SuggestedToolCard(
        id='sleep-wind-down',
        title='Sleep Wind-down',
        description='Gentle night support and audio prompts.',
        icon='moon',
        tint='#4338ca',
        tint_bg='#e0e7ff',
    ),
]

MOOD_SCORES = {
    'overwhelmed': 1,
    'confused': 2,
    'okay': 3,
    'better': 4,
    'calm': 5,
}


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


def get_current_account(
    db: Session,
    current_user: dict,
) -> tuple[User, UserDetail | None, dict, str, str]:
    email = str(current_user.get('sub', '')).strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='App account not found')

    detail = db.execute(select(UserDetail).where(UserDetail.user_id == user.id)).scalar_one_or_none()
    state = detail.onboarding_state if detail and isinstance(detail.onboarding_state, dict) else {}
    full_name = (detail.full_name if detail and detail.full_name else '').strip()
    if not full_name:
        full_name = email.split('@')[0].replace('.', ' ').title()
    primary_goal = _normalize_goal(str(state.get('primary_goal') or ''))
    return user, detail, state, full_name, primary_goal


def _normalize_goal(goal: str) -> str:
    value = goal.strip().lower()
    if value in {'friendships_social', 'friendships'}:
        return 'friendships'
    if value in {'focus_procrastination', 'focus'}:
        return 'focus'
    if value in {'parenting_support', 'parenting'}:
        return 'parenting'
    return value


def _build_tool_list(primary_goal: str) -> list[SuggestedToolCard]:
    if not primary_goal:
        return TOOLS[:4]
    matched = [
        tool
        for tool in TOOLS
        if primary_goal.replace('_', ' ') in tool.title.lower() or primary_goal.replace('_', ' ') in tool.description.lower()
    ]
    if matched:
        seen = {tool.id for tool in matched}
        return [*matched[:2], *[tool for tool in TOOLS if tool.id not in seen][:2]]
    if primary_goal == 'friendships':
        tool_ids = {'question-builder', 'behavior-experiment', 'thought-reframe', 'mood-journal'}
        return [tool for tool in TOOLS if tool.id in tool_ids][:4]
    return TOOLS[:4]


def _select_latest_thread(db: Session, user_id: int) -> tuple[ChatThread | None, ChatMessage | None]:
    thread = db.execute(
        select(ChatThread).where(ChatThread.user_id == user_id).order_by(desc(ChatThread.thread_date), desc(ChatThread.id)).limit(1)
    ).scalar_one_or_none()
    if not thread:
        return None, None
    message = db.execute(
        select(ChatMessage).where(ChatMessage.thread_id == thread.id).order_by(desc(ChatMessage.id)).limit(1)
    ).scalar_one_or_none()
    return thread, message


def _build_focus_card(primary_goal: str, thread: ChatThread | None, last_message: ChatMessage | None) -> DashboardFocusCard:
    section_title = f'Built around {primary_goal.replace("_", " ")}' if primary_goal else 'Resume where you left off'
    if thread:
        title = thread.title.replace('-', ' ')
        hint = (last_message.content if last_message else 'Resume your latest coach thread.').strip()
        hint = hint[:120] + ('...' if len(hint) > 120 else '')
        return DashboardFocusCard(
            section_title=section_title,
            title=title.title(),
            hint=hint or 'Resume your latest coach thread.',
            tag=primary_goal.title() if primary_goal else 'Coach',
            next_step='Try this next: reopen the thought you saved and test one calmer interpretation.',
        )

    goal_title = primary_goal.replace('_', ' ').title() if primary_goal else 'Reflection'
    return DashboardFocusCard(
        section_title=section_title,
        title=f'New {goal_title.lower()} support',
        hint='You saved one reframe and a small observation exercise.',
        tag=goal_title,
        next_step='Try this next: notice 3 interactions before deciding how the whole situation feels.',
    )


def _checkin_query(user_id: int) -> Select[tuple[MoodCheckin]]:
    return select(MoodCheckin).where(MoodCheckin.user_id == user_id).order_by(desc(MoodCheckin.checkin_date), desc(MoodCheckin.id))


def _score_for_mood(mood_id: str) -> int:
    return MOOD_SCORES.get(mood_id, 3)


def _build_trend_summary(checkins: list[MoodCheckin]) -> MoodTrendSummary:
    return MoodTrendSummary(**build_trend_summary_data(checkins, _score_for_mood))


def _build_trend_points(checkins: list[MoodCheckin]) -> list[MoodTrendPoint]:
    return [
        MoodTrendPoint(
            date=item.checkin_date.isoformat(),
            mood_id=item.mood_id,
            mood_label=item.mood_label,
            score=_score_for_mood(item.mood_id),
        )
        for item in checkins
    ]


def build_mood_report_payload(checkins: list[MoodCheckin], range_days: int) -> dict:
    ordered = sorted(checkins, key=lambda item: (item.checkin_date, item.id))
    trend = _build_trend_summary(ordered)
    points = _build_trend_points(ordered)
    latest = ordered[-1].mood_label if ordered else None
    return {
        'range_days': range_days,
        'summary': {
            'average_mood': describe_mood_pattern(ordered),
            'average_score': trend.average_score,
            'latest_mood': latest,
            'streak_days': _calculate_streak(ordered, datetime.now(timezone.utc).date()),
            'total_checkins': len(ordered),
        },
        'trend': trend,
        'points': [point.model_dump() for point in points],
        'entries': [
            {
                'id': item.id,
                'mood_id': item.mood_id,
                'mood_label': item.mood_label,
                'checkin_date': item.checkin_date.isoformat(),
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
                'score': _score_for_mood(item.mood_id),
            }
            for item in ordered
        ],
    }


def _calculate_streak(checkins: list[MoodCheckin], today: date) -> int:
    if not checkins:
        return 0
    dates = {item.checkin_date for item in checkins}
    cursor = today
    if cursor not in dates and (today - timedelta(days=1)) in dates:
        cursor = today - timedelta(days=1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _build_stats(
    user: User,
    state: dict,
    checkins: list[MoodCheckin],
    today: date,
) -> list[DashboardStatCard]:
    streak = _calculate_streak(checkins, today)
    reminder_pref = str(state.get('reminder_preference') or '')
    fallback_minutes = 10 if reminder_pref == 'daily' else 8 if reminder_pref == 'few_times_week' else 6
    progress_minutes = min(max(len(checkins[-7:]) * 2, 0), fallback_minutes)

    return [
        DashboardStatCard(
            id='streak',
            label='Streak',
            accent='#7c3aed',
            value=f'{streak} days',
            hint='Consistency builds momentum.' if streak else 'Start a steady rhythm with one small check-in.',
        ),
        DashboardStatCard(
            id='daily_goal',
            label='Daily goal',
            accent='#d946ef',
            value=f'{progress_minutes} / {fallback_minutes} min',
            hint='Small sessions count.' if checkins else 'Gentle progress still moves the day forward.',
            progress_percent=min(int((progress_minutes / fallback_minutes) * 100), 100) if fallback_minutes else 0,
        ),
    ]


def build_home_dashboard(db: Session, current_user: dict) -> HomeDashboardResponse:
    user, _, state, full_name, primary_goal = get_current_account(db, current_user)
    title, subtitle = _dashboard_copy(primary_goal, full_name)
    today = datetime.now(timezone.utc).date()
    checkins = list(reversed(db.execute(_checkin_query(user.id)).scalars().all()))
    today_checkin = next((item for item in reversed(checkins) if item.checkin_date == today), None)
    thread, last_message = _select_latest_thread(db, user.id)

    return HomeDashboardResponse(
        header=DashboardHeader(title=title, subtitle=subtitle),
        mood_check=MoodCheckSection(
            title="Today's check-in",
            prompt='How are you feeling?',
            description='A quick mood check personalizes your self-help journey.',
            icon='smile',
            options=MOOD_OPTIONS,
            selected_mood_id=today_checkin.mood_id if today_checkin else None,
            selected_mood_label=today_checkin.mood_label if today_checkin else None,
            selected_at=today_checkin.updated_at.isoformat() if today_checkin else None,
        ),
        stats=_build_stats(user, state, checkins, today),
        mood_trend_preview=MoodTrendPreview(
            title='Mood trend',
            summary=_build_trend_summary(checkins[-7:]),
            points=_build_trend_points(checkins[-7:]),
            cta_label='View report',
        ),
        focus_card=_build_focus_card(primary_goal, thread, last_message),
        suggested_tools=_build_tool_list(primary_goal),
    )


@router.get('/home', response_model=HomeDashboardResponse)
def get_home_dashboard(
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> HomeDashboardResponse:
    return build_home_dashboard(db, current_user)
