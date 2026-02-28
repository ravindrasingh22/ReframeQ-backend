from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    message: str
    language: str = 'en'  # en | hinglish
    thread_id: int | None = None


class ChatMessageResponse(BaseModel):
    reply: str
    model: str
    thread_id: int
    thread_title: str


class ChatMessageItem(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class ChatThreadItem(BaseModel):
    id: int
    title: str
    thread_date: str
    created_at: str
    preview: str | None = None


class ChatThreadsResponse(BaseModel):
    items: list[ChatThreadItem]


class ChatThreadDetailResponse(BaseModel):
    thread: ChatThreadItem
    messages: list[ChatMessageItem]
