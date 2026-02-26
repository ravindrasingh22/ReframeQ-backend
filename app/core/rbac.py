from collections.abc import Iterable
from typing import Literal

Role = Literal['admin', 'content_editor', 'support', 'analyst', 'app_user']
Permission = Literal[
    'users.read_limited',
    'users.manage_issues',
    'content.read',
    'content.write',
    'ai.read',
    'ai.write',
    'safety.read',
    'safety.write',
    'analytics.read',
    'audit.read',
    'settings.read',
    'settings.write',
    'app.use'
]

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    'admin': {
        'users.read_limited',
        'users.manage_issues',
        'content.read',
        'content.write',
        'ai.read',
        'ai.write',
        'safety.read',
        'safety.write',
        'analytics.read',
        'audit.read',
        'settings.read',
        'settings.write',
        'app.use'
    },
    'content_editor': {
        'content.read',
        'content.write'
    },
    'support': {
        'users.read_limited',
        'users.manage_issues'
    },
    'analyst': {
        'analytics.read'
    },
    'app_user': {
        'app.use'
    }
}

ADMIN_ROLES: set[Role] = {'admin', 'content_editor', 'support', 'analyst'}


def permissions_for_role(role: str) -> set[Permission]:
    return ROLE_PERMISSIONS.get(role, set())


def has_permissions(role: str, required_permissions: Iterable[Permission]) -> bool:
    assigned = permissions_for_role(role)
    return set(required_permissions).issubset(assigned)
