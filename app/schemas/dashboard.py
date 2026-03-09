from pydantic import BaseModel


class DashboardHeader(BaseModel):
    title: str
    subtitle: str


class MoodOption(BaseModel):
    id: str
    label: str
    emoji: str


class MoodCheckSection(BaseModel):
    title: str
    prompt: str
    description: str
    icon: str
    options: list[MoodOption]
    selected_mood_id: str | None = None
    selected_mood_label: str | None = None
    selected_at: str | None = None


class DashboardStatCard(BaseModel):
    id: str
    label: str
    accent: str
    value: str
    hint: str
    progress_percent: int | None = None


class DashboardFocusCard(BaseModel):
    section_title: str
    title: str
    hint: str
    tag: str
    next_step: str


class SuggestedToolCard(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    tint: str
    tint_bg: str


class MoodTrendPoint(BaseModel):
    date: str
    mood_id: str
    mood_label: str
    score: int


class MoodTrendSummary(BaseModel):
    label: str
    direction: str
    detail: str
    average_score: float
    latest_mood_label: str | None = None


class MoodTrendPreview(BaseModel):
    title: str
    summary: MoodTrendSummary
    points: list[MoodTrendPoint]
    cta_label: str


class HomeDashboardResponse(BaseModel):
    header: DashboardHeader
    mood_check: MoodCheckSection
    stats: list[DashboardStatCard]
    mood_trend_preview: MoodTrendPreview
    focus_card: DashboardFocusCard
    suggested_tools: list[SuggestedToolCard]
