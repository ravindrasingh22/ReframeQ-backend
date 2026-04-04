from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_app_permissions
from app.db.session import get_db
from app.models import AuditLog, ChatMessage, ChatThread, User, UserDetail
from app.schemas.chat import (
    ChatMessageItem,
    ChatMessageRequest,
    ChatMessageResponse,
    SafetyDecisionResponse,
    SafetySupportAction,
    SafetySupportCard,
    ChatThreadDetailResponse,
    ChatThreadItem,
    ChatThreadsResponse,
)
from app.services.emergency_support_service import load_emergency_support_configuration, load_emergency_support_state, select_emergency_resource
from app.services.ollama_service import generate_chat_reply

router = APIRouter()


def _classify_risk(message: str, history: list[tuple[str, str]], config: dict) -> SafetyDecisionResponse:
    normalized = message.strip().lower()
    keywords = config.get('risk_keywords', {})
    trigger_codes: list[str] = []

    def has_match(values: list[str]) -> bool:
        matched = [value for value in values if value and value in normalized]
        trigger_codes.extend(matched)
        return bool(matched)

    if has_match(list(keywords.get('critical', []))):
        return SafetyDecisionResponse(
            risk_score='critical',
            safety_level='crisis_danger',
            trigger_codes=trigger_codes,
            recommended_action='emergency_support',
            requires_interrupt=True,
        )
    if has_match(list(keywords.get('high', []))):
        return SafetyDecisionResponse(
            risk_score='high',
            safety_level='crisis_danger',
            trigger_codes=trigger_codes,
            recommended_action='show_support_screen',
            requires_interrupt=True,
        )
    prior_distress = sum(
        1
        for role, content in history[-6:]
        if role == 'user'
        and any(term in content.lower() for term in list(keywords.get('medium', [])) + list(keywords.get('high', [])))
    )
    if has_match(list(keywords.get('medium', []))) or prior_distress >= 2:
        return SafetyDecisionResponse(
            risk_score='medium',
            safety_level='heightened_support',
            trigger_codes=trigger_codes or (['repeat_distress'] if prior_distress >= 2 else []),
            recommended_action='offer_support_options',
            requires_interrupt=False,
        )
    return SafetyDecisionResponse()


def _build_support_card(config: dict, resource: dict, contact: dict | None, decision: SafetyDecisionResponse) -> SafetySupportCard:
    copy = config.get('copy', {})
    title = str(copy.get('heightened_support_title', 'You may need human support soon'))
    body = str(copy.get('heightened_support_body', 'It sounds like things feel very heavy right now.'))
    if decision.risk_score in {'high', 'critical'}:
        title = str(copy.get('urgent_title', title))
        body = str(copy.get('urgent_body', body))

    actions = [
        SafetySupportAction(
            kind='call',
            label=str(resource.get('helpline_label', 'Call support helpline')),
            value=str((resource.get('helpline_numbers') or [''])[0]),
        ),
        SafetySupportAction(
            kind='call',
            label=str(resource.get('emergency_label', 'Call emergency')),
            value=str(resource.get('emergency_number', '')),
        ),
    ]
    if contact and contact.get('phone_number'):
        actions.append(
            SafetySupportAction(
                kind='contact',
                label=f"Contact {contact.get('name', 'trusted person')}",
                value=str(contact.get('phone_number', '')),
            )
        )
    actions.append(
        SafetySupportAction(
            kind='link',
            label='Find nearby support',
            value=str(resource.get('support_search_url', '')),
        )
    )
    actions.append(
        SafetySupportAction(
            kind='acknowledge',
            label=str(copy.get('safe_for_now_label', 'I am safe for now')),
            value='safe_for_now',
        )
    )
    return SafetySupportCard(title=title, body=body, actions=actions)


def _get_current_account(db: Session, current_user: dict) -> tuple[User, str]:
    email = str(current_user.get('sub', '')).strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='App account not found')

    detail = db.execute(select(UserDetail).where(UserDetail.user_id == user.id)).scalar_one_or_none()
    full_name = ''
    if detail and detail.full_name and detail.full_name.strip():
        full_name = detail.full_name.strip()
    if not full_name:
        full_name = email.split('@')[0].replace('.', ' ').title()
    return user, full_name


def _get_account_context(db: Session, current_user: dict) -> tuple[User, UserDetail | None, str]:
    user, full_name = _get_current_account(db, current_user)
    detail = db.execute(select(UserDetail).where(UserDetail.user_id == user.id)).scalar_one_or_none()
    return user, detail, full_name


def _serialize_thread(thread: ChatThread, preview: str | None = None) -> ChatThreadItem:
    return ChatThreadItem(
        id=thread.id,
        title=thread.title,
        thread_date=thread.thread_date,
        created_at=thread.created_at.isoformat(),
        preview=preview,
    )


@router.get('/threads', response_model=ChatThreadsResponse)
def list_threads(
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> ChatThreadsResponse:
    user, _ = _get_current_account(db, current_user)
    threads = db.execute(
        select(ChatThread).where(ChatThread.user_id == user.id).order_by(ChatThread.thread_date.desc(), ChatThread.id.desc())
    ).scalars().all()

    items: list[ChatThreadItem] = []
    for thread in threads:
        last = db.execute(
            select(ChatMessage).where(ChatMessage.thread_id == thread.id).order_by(ChatMessage.id.desc()).limit(1)
        ).scalar_one_or_none()
        items.append(_serialize_thread(thread, preview=last.content if last else None))
    return ChatThreadsResponse(items=items)


@router.get('/threads/{thread_id}', response_model=ChatThreadDetailResponse)
def get_thread(
    thread_id: int,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> ChatThreadDetailResponse:
    user, _ = _get_current_account(db, current_user)
    thread = db.execute(
        select(ChatThread).where(ChatThread.id == thread_id, ChatThread.user_id == user.id)
    ).scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Thread not found')

    messages = db.execute(
        select(ChatMessage).where(ChatMessage.thread_id == thread.id).order_by(ChatMessage.id.asc())
    ).scalars().all()

    return ChatThreadDetailResponse(
        thread=_serialize_thread(thread),
        messages=[
            ChatMessageItem(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at.isoformat(),
            )
            for message in messages
        ],
    )


@router.post('/message', response_model=ChatMessageResponse)
def send_chat_message(
    payload: ChatMessageRequest,
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
    db: Annotated[Session, Depends(get_db)],
) -> ChatMessageResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='message is required')

    user, detail, full_name = _get_account_context(db, current_user)
    today = datetime.now(timezone.utc).date().isoformat()

    thread: ChatThread | None = None
    if payload.thread_id:
        thread = db.execute(
            select(ChatThread).where(ChatThread.id == payload.thread_id, ChatThread.user_id == user.id)
        ).scalar_one_or_none()
        if not thread:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Thread not found')
    else:
        thread = db.execute(
            select(ChatThread).where(ChatThread.user_id == user.id, ChatThread.thread_date == today)
        ).scalar_one_or_none()
        if not thread:
            thread = ChatThread(user_id=user.id, title=f'{full_name}-{today}', thread_date=today)
            db.add(thread)
            db.flush()

    history_messages = db.execute(
        select(ChatMessage).where(ChatMessage.thread_id == thread.id).order_by(ChatMessage.id.asc()).limit(30)
    ).scalars().all()
    history = [(msg.role, msg.content) for msg in history_messages]

    user_message = ChatMessage(thread_id=thread.id, role='user', content=message)
    db.add(user_message)

    config = load_emergency_support_configuration(db)
    decision = _classify_risk(message, history, config)
    feature_enabled = bool(config.get('enabled', True))
    support_card = None

    try:
        if feature_enabled and decision.risk_score in {'medium', 'high', 'critical'}:
            prompts = config.get('prompts', {})
            if decision.risk_score == 'critical':
                reply = str(prompts.get('danger_reply', 'Please contact emergency help or a support helpline right away.'))
            elif decision.risk_score == 'high':
                reply = str(prompts.get('urgent_reply', 'Please contact a trusted person or support helpline right now.'))
            else:
                reply = str(prompts.get('heightened_support_reply', 'Let us focus on getting you support from a person right now.'))
            model = 'emergency-support'
            decision.feature_applied = True
            resource = select_emergency_resource(config, detail.country if detail else '')
            trusted_contacts = load_emergency_support_state(detail).get('trusted_contacts', [])
            primary_contact = next((item for item in trusted_contacts if item.get('is_primary')), trusted_contacts[0] if trusted_contacts else None)
            support_card = _build_support_card(config, resource, primary_contact, decision)
        else:
            reply, model = generate_chat_reply(message=message, language=payload.language, history=history)
    except httpx.HTTPError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f'LLM service unavailable ({type(exc).__name__}): {exc}',
        ) from exc

    if feature_enabled and decision.feature_applied and config.get('review_rules', {}).get('enabled', True):
        db.add(
            AuditLog(
                actor_email=current_user.get('sub', ''),
                action='emergency_support_review_created',
                module='safety-support',
                details=(
                    f'user_id={user.id};thread_id={thread.id};risk_score={decision.risk_score};'
                    f"requires_interrupt={decision.requires_interrupt};triggers={','.join(decision.trigger_codes)}"
                ),
            )
        )
    assistant_message = ChatMessage(thread_id=thread.id, role='assistant', content=reply)
    db.add(assistant_message)
    db.commit()

    return ChatMessageResponse(
        reply=reply,
        model=model,
        thread_id=thread.id,
        thread_title=thread.title,
        safety_decision=decision,
        support_card=support_card,
    )


@router.get('/health')
def chat_health(
    current_user: Annotated[dict, Depends(require_app_permissions('app.use'))],
) -> dict:
    try:
        _, model = generate_chat_reply(message='health check', language='en')
        return {'status': 'ok', 'model': model}
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f'ollama_unreachable ({type(exc).__name__}): {exc}',
        ) from exc
