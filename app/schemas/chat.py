from pydantic import BaseModel, Field


class SafetyDecisionResponse(BaseModel):
    risk_score: str = 'low'
    safety_level: str = 'support'
    trigger_codes: list[str] = Field(default_factory=list)
    recommended_action: str = 'continue'
    requires_interrupt: bool = False
    feature_applied: bool = False


class SafetySupportAction(BaseModel):
    kind: str
    label: str
    value: str = ''


class SafetySupportCard(BaseModel):
    title: str = ''
    body: str = ''
    actions: list[SafetySupportAction] = Field(default_factory=list)


class ChatMessageRequest(BaseModel):
    message: str
    language: str = 'en'  # en | hinglish
    thread_id: int | None = None


class ChatMessageResponse(BaseModel):
    reply: str
    model: str
    thread_id: int
    thread_title: str
    safety_decision: SafetyDecisionResponse = Field(default_factory=SafetyDecisionResponse)
    support_card: SafetySupportCard | None = None


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
