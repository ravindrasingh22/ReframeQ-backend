from datetime import datetime, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_app_permissions
from app.db.session import get_db
from app.models import ChatMessage, ChatThread, User, UserDetail
from app.schemas.chat import (
    ChatMessageItem,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatThreadDetailResponse,
    ChatThreadItem,
    ChatThreadsResponse,
)
from app.services.ollama_service import generate_chat_reply

router = APIRouter()


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

    user, full_name = _get_current_account(db, current_user)
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

    try:
        reply, model = generate_chat_reply(message=message, language=payload.language, history=history)
    except httpx.HTTPError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f'LLM service unavailable ({type(exc).__name__}): {exc}',
        ) from exc

    assistant_message = ChatMessage(thread_id=thread.id, role='assistant', content=reply)
    db.add(assistant_message)
    db.commit()

    return ChatMessageResponse(reply=reply, model=model, thread_id=thread.id, thread_title=thread.title)


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
