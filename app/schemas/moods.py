from pydantic import BaseModel

from app.schemas.dashboard import DashboardStatCard, MoodTrendSummary


class MoodCheckinRequest(BaseModel):
    mood_id: str


class MoodCheckinSummary(BaseModel):
    mood_id: str
    mood_label: str
    selected_at: str


class MoodCheckinResponse(BaseModel):
    checkin: MoodCheckinSummary
    stats: list[DashboardStatCard]


class MoodReportEntry(BaseModel):
    id: int
    mood_id: str
    mood_label: str
    checkin_date: str
    created_at: str
    updated_at: str
    score: int


class MoodReportSummary(BaseModel):
    average_mood: str
    average_score: float
    latest_mood: str | None = None
    streak_days: int
    total_checkins: int


class MoodReportResponse(BaseModel):
    range_days: int
    summary: MoodReportSummary
    trend: MoodTrendSummary
    points: list[dict]
    entries: list[MoodReportEntry]
