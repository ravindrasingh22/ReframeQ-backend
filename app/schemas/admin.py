from pydantic import BaseModel


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
    role: str
    is_active: bool
    country: str
    language: str
    member_since: str | None = None


class UpdateUserProfileRequest(BaseModel):
    full_name: str | None = None
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
