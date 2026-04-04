from pydantic import BaseModel, Field


class LanguageOption(BaseModel):
    code: str
    name: str
    enabled: bool


class SupportedLanguagesResponse(BaseModel):
    supported_languages: list[str]
    options: list[LanguageOption]


class UpdateSupportedLanguagesRequest(BaseModel):
    supported_languages: list[str]


class PromptTemplateItem(BaseModel):
    key: str
    label: str
    system_prompt: str = ''
    developer_prompt: str = ''
    enabled: bool = True


class PromptTemplatesResponse(BaseModel):
    items: list[PromptTemplateItem] = Field(default_factory=list)


class UpdatePromptTemplatesRequest(BaseModel):
    items: list[PromptTemplateItem] = Field(default_factory=list)


class ModelConfigurationResponse(BaseModel):
    provider: str = 'ollama'
    default_model: str = 'mistral'
    onboarding_model: str = 'mistral'
    fallback_model: str = 'mistral'
    base_url: str = 'http://localhost:11434'
    timeout_seconds: int = 60
    temperature: float = 0.2
    enabled: bool = True


class UpdateModelConfigurationRequest(BaseModel):
    provider: str = 'ollama'
    default_model: str
    onboarding_model: str
    fallback_model: str
    base_url: str
    timeout_seconds: int = 60
    temperature: float = 0.2
    enabled: bool = True


class AppSessionConfigurationResponse(BaseModel):
    app_session_duration_days: int = Field(default=30, ge=1, le=365)


class UpdateAppSessionConfigurationRequest(BaseModel):
    app_session_duration_days: int = Field(default=30, ge=1, le=365)


class OnboardingTextScreenConfig(BaseModel):
    key: str
    title: str
    subtitle: str = ''
    primary_cta: str = 'Continue'
    secondary_cta: str = ''
    enabled: bool = True


class OnboardingTextConfigurationResponse(BaseModel):
    screens: list[OnboardingTextScreenConfig] = Field(default_factory=list)


class UpdateOnboardingTextConfigurationRequest(BaseModel):
    screens: list[OnboardingTextScreenConfig] = Field(default_factory=list)


class UserTypeToggle(BaseModel):
    key: str
    label: str
    enabled: bool = True


class AccountModeToggle(BaseModel):
    key: str
    label: str
    enabled: bool = True


class OnboardingPolicyConfigurationResponse(BaseModel):
    onboarding_enabled: bool = True
    allow_resume: bool = True
    enabled_user_types: list[UserTypeToggle] = Field(default_factory=list)
    enabled_account_modes: list[AccountModeToggle] = Field(default_factory=list)
    allow_family_flows: bool = True
    require_invite_for_family_join: bool = True


class UpdateOnboardingPolicyConfigurationRequest(BaseModel):
    onboarding_enabled: bool = True
    allow_resume: bool = True
    enabled_user_types: list[UserTypeToggle] = Field(default_factory=list)
    enabled_account_modes: list[AccountModeToggle] = Field(default_factory=list)
    allow_family_flows: bool = True
    require_invite_for_family_join: bool = True


class EmergencySupportResource(BaseModel):
    country: str
    helpline_label: str
    helpline_numbers: list[str] = Field(default_factory=list)
    emergency_label: str
    emergency_number: str = ''
    support_search_url: str = ''


class EmergencySupportCopy(BaseModel):
    profile_title: str = 'Emergency Support Path'
    profile_description: str = 'Add trusted people and support options so help is easier to reach in a hard moment.'
    reminder_title: str = 'Complete your support setup'
    reminder_body: str = 'Add at least one trusted contact so ReframeQ can show the fastest support options when needed.'
    heightened_support_title: str = 'You may need human support soon'
    heightened_support_body: str = 'It sounds like things feel very heavy right now. If it helps, reach out to a trusted person or support service.'
    urgent_title: str = 'We are concerned you may need immediate human support'
    urgent_body: str = 'You do not have to handle this alone. ReframeQ is not an emergency service. Please contact a trusted person, a support helpline, or emergency help right now.'
    safe_for_now_label: str = 'I am safe for now'


class EmergencySupportTrustedContactRules(BaseModel):
    min_contacts: int = 1
    max_contacts: int = 3
    show_call_shortcut: bool = True


class EmergencySupportReviewRules(BaseModel):
    enabled: bool = True
    log_detection_events: bool = True


class EmergencySupportPromptSet(BaseModel):
    heightened_support_reply: str = (
        'I am sorry this feels so heavy. Let us keep this simple and focus on getting you support from a person right now.'
    )
    urgent_reply: str = (
        'I am concerned you may need human support right now. Please contact a trusted person, a support helpline, or emergency help as soon as you can.'
    )
    danger_reply: str = (
        'I am concerned about your safety right now. Please call emergency help or a support helpline right away, and contact someone you trust if possible.'
    )


class EmergencySupportConfigurationResponse(BaseModel):
    enabled: bool = True
    risk_keywords: dict[str, list[str]] = Field(default_factory=dict)
    copy: EmergencySupportCopy = Field(default_factory=EmergencySupportCopy)
    resources: list[EmergencySupportResource] = Field(default_factory=list)
    trusted_contact_rules: EmergencySupportTrustedContactRules = Field(default_factory=EmergencySupportTrustedContactRules)
    prompts: EmergencySupportPromptSet = Field(default_factory=EmergencySupportPromptSet)
    review_rules: EmergencySupportReviewRules = Field(default_factory=EmergencySupportReviewRules)


class UpdateEmergencySupportConfigurationRequest(BaseModel):
    enabled: bool = True
    risk_keywords: dict[str, list[str]] = Field(default_factory=dict)
    copy: EmergencySupportCopy = Field(default_factory=EmergencySupportCopy)
    resources: list[EmergencySupportResource] = Field(default_factory=list)
    trusted_contact_rules: EmergencySupportTrustedContactRules = Field(default_factory=EmergencySupportTrustedContactRules)
    prompts: EmergencySupportPromptSet = Field(default_factory=EmergencySupportPromptSet)
    review_rules: EmergencySupportReviewRules = Field(default_factory=EmergencySupportReviewRules)
