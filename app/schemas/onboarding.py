from pydantic import BaseModel, Field


class InviteValidationRequest(BaseModel):
    invite_code: str


class InviteValidationResponse(BaseModel):
    valid: bool
    invite_code: str
    status: str
    account_mode: str
    invited_user_email: str | None = None


class SafetyScanRequest(BaseModel):
    message: str


class SafetyScanResponse(BaseModel):
    scan_status: str
    policy_code: str
    blocked_topics: list[str] = Field(default_factory=list)
    needs_handoff: bool = False


class OnboardingStatePayload(BaseModel):
    account_mode: str = ''
    invite_code: str = ''
    invite_validated: bool = False
    user_type: str = ''
    primary_goal: str = ''
    secondary_goals: list[str] = Field(default_factory=list)
    clarity: int = 0
    control: int = 0
    noise: int = 0
    readiness: int = 0
    coach_style: str = ''
    first_thought: str = ''
    safety_flag: str = 'none'
    full_name: str = ''
    email: str = ''
    reminder_preference: str = ''
    child_display_name: str = ''
    child_age_band: str = ''
    daily_time_limit: str = ''
    topic_restrictions: str = ''
    visibility_rule: str = ''
    guardian_consent: bool = False
    onboarding_complete: bool = False
    language: str = 'en'
    country: str = ''
    first_reframe_snapshot: dict = Field(default_factory=dict)


class SaveOnboardingRequest(BaseModel):
    step: str
    completed: bool = False
    state: OnboardingStatePayload


class OnboardingSummary(BaseModel):
    step: str
    completed: bool
    state: OnboardingStatePayload
    updated_at: str | None = None


class AppProfileResponse(BaseModel):
    email: str
    role: str
    full_name: str
    country: str
    language: str
    account_mode: str
    user_type: str
    primary_goal: str
    coach_style: str
    onboarding: OnboardingSummary
    dashboard_title: str
    dashboard_subtitle: str


class OnboardingToggleItem(BaseModel):
    key: str
    label: str
    enabled: bool = True


class OnboardingScreenTextItem(BaseModel):
    key: str
    title: str
    subtitle: str = ''
    primary_cta: str = 'Continue'
    secondary_cta: str = ''
    enabled: bool = True


class OnboardingPolicySummary(BaseModel):
    onboarding_enabled: bool = True
    allow_resume: bool = True
    allow_family_flows: bool = True
    require_invite_for_family_join: bool = True
    enabled_user_types: list[OnboardingToggleItem] = Field(default_factory=list)
    enabled_account_modes: list[OnboardingToggleItem] = Field(default_factory=list)


class OnboardingConfigurationResponse(BaseModel):
    policy: OnboardingPolicySummary
    text: list[OnboardingScreenTextItem] = Field(default_factory=list)
