from pydantic import BaseModel, Field


class UserListItem(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    account_state: str
    member_since: str | None = None


class UsersListResponse(BaseModel):
    requested_by: str
    visibility: str
    users: list[UserListItem]


class UpdateUserRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class CreateUserRequest(BaseModel):
    email: str
    full_name: str = ''
    role: str
    is_active: bool = True
    country: str = ''
    language: str = 'en'
    temp_password: str = 'change-me'


class UserProfileResponse(BaseModel):
    user_id: int
    email: str
    full_name: str
    mobile_country_code: str = ''
    mobile_number: str = ''
    city: str = ''
    state: str = ''
    role: str
    is_active: bool
    country: str
    language: str
    member_since: str | None = None
    invite_code: str | None = None
    onboarding_step: str = 'welcome'
    onboarding_completed: bool = False
    onboarding_updated_at: str | None = None
    onboarding_state: dict = Field(default_factory=dict)
    mood_logs: list['MoodLogItem'] = Field(default_factory=list)


class MoodLogItem(BaseModel):
    id: int
    mood_id: str
    mood_label: str
    checkin_date: str
    created_at: str
    updated_at: str


class UpdateUserProfileRequest(BaseModel):
    full_name: str | None = None
    mobile_country_code: str | None = None
    mobile_number: str | None = None
    city: str | None = None
    state: str | None = None
    role: str | None = None
    is_active: bool | None = None
    country: str | None = None
    language: str | None = None


class ChangePasswordRequest(BaseModel):
    new_password: str


class BulkUserActionRequest(BaseModel):
    user_ids: list[int]
    action: str  # set_status | set_role | delete
    is_active: bool | None = None
    role: str | None = None


class JourneyItem(BaseModel):
    id: int
    title: str
    topic: str
    difficulty: str
    is_published: bool
    summary: str


class JourneyCreateRequest(BaseModel):
    title: str
    topic: str
    difficulty: str
    summary: str
    is_published: bool = False


class JourneyListResponse(BaseModel):
    requested_by: str
    items: list[JourneyItem]


class AnalyticsSummary(BaseModel):
    dau: int
    journey_completion_rate: int
    sensitive_content_detections: int
    top_journey: str


class AnalyticsOverviewResponse(BaseModel):
    requested_by: str
    summary: AnalyticsSummary


class AuditLogItem(BaseModel):
    id: int
    actor_email: str
    actor_role: str | None = None
    action: str
    module: str
    details: str
    created_at: str


class AuditListResponse(BaseModel):
    requested_by: str
    events: list[AuditLogItem]


class FirstReframeConfigResponse(BaseModel):
    enabled: bool
    model_name: str
    temperature: float
    max_tokens: int
    schema_version: str
    show_pattern_label: bool
    show_titles: bool
    system_prompt: str
    developer_prompt: str
    fallback_template_json: dict = Field(default_factory=dict)
    style_overrides: dict = Field(default_factory=dict)
    goal_overrides: dict = Field(default_factory=dict)
    user_type_overrides: dict = Field(default_factory=dict)
    safety_overrides: dict = Field(default_factory=dict)


class FirstReframeConfigUpdateRequest(BaseModel):
    enabled: bool = True
    model_name: str
    temperature: float = 0.2
    max_tokens: int = 220
    schema_version: str
    show_pattern_label: bool = True
    show_titles: bool = True
    system_prompt: str
    developer_prompt: str = ''
    fallback_template_json: dict = Field(default_factory=dict)
    style_overrides: dict = Field(default_factory=dict)
    goal_overrides: dict = Field(default_factory=dict)
    user_type_overrides: dict = Field(default_factory=dict)
    safety_overrides: dict = Field(default_factory=dict)


class FirstReframePreviewRequest(BaseModel):
    user_thought: str
    user_type: str = 'adult'
    account_mode: str = 'individual'
    goal: str = 'overthinking'
    secondary_goals: list[str] = Field(default_factory=list)
    clarity_score: int | None = None
    control_score: int | None = None
    mental_noise_score: int | None = None
    readiness_score: int | None = None
    coach_style: str = 'gentle'
    language: str = 'en'
    country: str = 'US'


class FirstReframePreviewResponse(BaseModel):
    model: str
    result: dict = Field(default_factory=dict)
