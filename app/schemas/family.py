from pydantic import BaseModel, Field


class CreateFamilyProfileRequest(BaseModel):
    profile_type: str = 'child'  # child | adult
    display_name: str
    age_band: str = '13_15'
    daily_time_limit_minutes: int = Field(default=60, ge=10, le=240)
    topic_restrictions: list[str] = []
    conversation_visibility_rule: str = 'summary_only'


class UpdateChildProfileRequest(BaseModel):
    display_name: str | None = None
    age_band: str | None = None
    daily_time_limit_minutes: int | None = Field(default=None, ge=10, le=240)
    topic_restrictions: list[str] | None = None
    conversation_visibility_rule: str | None = None


class UpdateChildStatusRequest(BaseModel):
    profile_active: bool


class RecordGuardianConsentRequest(BaseModel):
    guardian_user_id: int
    consent_text_version: str = 'v1'


class FamilyProfileItem(BaseModel):
    profile_id: int
    primary_user_id: int
    profile_type: str
    display_name: str
    age_band: str
    profile_active: bool
    consent_granted: bool | None
    consent_text_version: str | None
    daily_time_limit_minutes: int | None
    topic_restrictions: list[str]
    conversation_visibility_rule: str | None


class FamilyProfilesResponse(BaseModel):
    requested_by: str
    primary_user_id: int
    items: list[FamilyProfileItem]


# Backward-compatible aliases for existing UI code.
ChildProfileItem = FamilyProfileItem
FamilyOverviewResponse = FamilyProfilesResponse
