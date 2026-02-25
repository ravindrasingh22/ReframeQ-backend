from app.core.rbac import ADMIN_ROLES, Role
from app.core.security import create_access_token


# Placeholder logic; replace with DB-backed password verification.
def resolve_role_from_email(email: str) -> Role:
    normalized = email.lower()
    if normalized.endswith('@admin.reframeq.local'):
        return 'admin'
    if normalized.endswith('@editor.reframeq.local'):
        return 'content_editor'
    if normalized.endswith('@support.reframeq.local'):
        return 'support'
    if normalized.endswith('@analyst.reframeq.local'):
        return 'analyst'
    return 'app_user'


def login(email: str, password: str) -> tuple[str, str]:
    role = resolve_role_from_email(email)
    token = create_access_token(subject=email, role=role)
    return token, role


def is_admin_console_role(role: str) -> bool:
    return role in ADMIN_ROLES
