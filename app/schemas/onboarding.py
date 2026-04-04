from __future__ import annotations

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
    mobile_country_code: str = ''
    mobile_number: str = ''
    city: str = ''
    state: str = ''
    country: str
    language: str
    account_mode: str
    user_type: str
    primary_goal: str
    coach_style: str
    onboarding: OnboardingSummary
    dashboard_title: str
    dashboard_subtitle: str
    emergency_support: 'AppEmergencySupportProfile'


class UpdateAppProfileRequest(BaseModel):
    full_name: str | None = None
    mobile_country_code: str | None = None
    mobile_number: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    language: str | None = None
    emergency_support: 'UpdateAppEmergencySupportRequest | None' = None


class ChangeAppPasswordRequest(BaseModel):
    new_password: str


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


class TrustedContactItem(BaseModel):
    id: str
    name: str
    relationship: str = ''
    phone_number: str = ''
    email: str = ''
    preferred_language: str = 'en'
    city: str = ''
    state: str = ''
    is_primary: bool = False
    show_call_shortcut: bool = True
    support_note: str = ''
    active: bool = True


class UpdateTrustedContactItem(BaseModel):
    id: str | None = None
    name: str
    relationship: str = ''
    phone_number: str = ''
    email: str = ''
    preferred_language: str = 'en'
    city: str = ''
    state: str = ''
    is_primary: bool = False
    show_call_shortcut: bool = True
    support_note: str = ''
    active: bool = True


class AppEmergencySupportResourceSummary(BaseModel):
    country: str = ''
    helpline_label: str = ''
    helpline_numbers: list[str] = Field(default_factory=list)
    emergency_label: str = ''
    emergency_number: str = ''
    support_search_url: str = ''


class AppEmergencySupportProfile(BaseModel):
    enabled: bool = False
    eligible: bool = False
    profile_complete: bool = False
    show_profile_prompt: bool = False
    title: str = 'Emergency Support Path'
    description: str = ''
    trusted_contacts: list[TrustedContactItem] = Field(default_factory=list)
    resource: AppEmergencySupportResourceSummary = Field(default_factory=AppEmergencySupportResourceSummary)


class UpdateAppEmergencySupportRequest(BaseModel):
    trusted_contacts: list[UpdateTrustedContactItem] = Field(default_factory=list)
