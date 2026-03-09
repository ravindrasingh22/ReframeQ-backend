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
