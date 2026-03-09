from typing import Literal

from pydantic import BaseModel, Field


OnboardingAIStep = Literal[
    'goal_microcopy',
    'clarity_interpretation',
    'style_confirmation',
    'tutorial_example',
    'first_reframe',
]

ScanStatus = Literal['allow', 'limit', 'block', 'handoff']


class OnboardingEntryContext(BaseModel):
    app_source: str = 'unknown'
    signup_path: str = 'direct_signup'
    language: str = 'en'
    country: str = 'US'
    is_new_user: bool = True
    is_resuming: bool = False


class OnboardingAccountContext(BaseModel):
    account_mode: str = 'individual'
    user_type: str = 'adult'


class OnboardingGoalContext(BaseModel):
    goal: str = 'overthinking'
    secondary_goals: list[str] = Field(default_factory=list)


class OnboardingStateContext(BaseModel):
    clarity_score: int | None = Field(default=None, ge=0, le=100)
    control_score: int | None = Field(default=None, ge=0, le=100)
    mental_noise_score: int | None = Field(default=None, ge=0, le=100)
    readiness_score: int | None = Field(default=None, ge=0, le=100)


class OnboardingStyleContext(BaseModel):
    coach_style: str = 'gentle'


class OnboardingFamilyContext(BaseModel):
    is_family_flow: bool = False
    family_role: str | None = None
    child_age_band: str | None = None
    visibility_mode: str | None = None
    topic_restrictions: list[str] = Field(default_factory=list)


class OnboardingInputContext(BaseModel):
    user_message: str | None = None
    detected_pattern: str = 'unknown'
    emotion_intensity_hint: str | None = None


class OnboardingSafetyContext(BaseModel):
    scan_status: ScanStatus = 'allow'
    policy_code: str = 'ok'
    blocked_topics: list[str] = Field(default_factory=list)
    needs_handoff: bool = False


class OnboardingAIContext(BaseModel):
    entry_context: OnboardingEntryContext = Field(default_factory=OnboardingEntryContext)
    account_context: OnboardingAccountContext = Field(default_factory=OnboardingAccountContext)
    goal_context: OnboardingGoalContext = Field(default_factory=OnboardingGoalContext)
    state_context: OnboardingStateContext = Field(default_factory=OnboardingStateContext)
    style_context: OnboardingStyleContext = Field(default_factory=OnboardingStyleContext)
    family_context: OnboardingFamilyContext = Field(default_factory=OnboardingFamilyContext)
    input_context: OnboardingInputContext = Field(default_factory=OnboardingInputContext)
    safety_context: OnboardingSafetyContext = Field(default_factory=OnboardingSafetyContext)


class OnboardingAIRequest(BaseModel):
    contract_version: str = '2026-03-07'
    surface: str = 'onboarding'
    step: OnboardingAIStep
    request_id: str | None = None
    timestamp: str | None = None
    context: OnboardingAIContext


class OnboardingAIResult(BaseModel):
    message: str | None = None
    situation: str | None = None
    thought: str | None = None
    reframe: str | None = None
    socratic_question: str | None = None
    next_step: str | None = None
    detected_pattern_label: str | None = None
    reframe_title: str | None = None
    reframe_text: str | None = None
    next_step_title: str | None = None
    next_step_text: str | None = None
    question_title: str | None = None
    question_text: str | None = None
    pattern_label: str | None = None
    config_version: str | None = None
    tone: str = 'gentle'
    fallback_used: bool = False


class OnboardingAISafetyDecision(BaseModel):
    scan_status: ScanStatus
    policy_code: str


class OnboardingAIResponse(BaseModel):
    step: OnboardingAIStep
    result: OnboardingAIResult
    model: str
    safety_decision: OnboardingAISafetyDecision
