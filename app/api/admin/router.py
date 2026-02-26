from fastapi import APIRouter

from app.api.admin import (
    routes_ai,
    routes_audit,
    routes_auth,
    routes_content,
    routes_family,
    routes_reports,
    routes_safety,
    routes_settings,
    routes_users,
)

router = APIRouter()
router.include_router(routes_auth.router, prefix='/auth', tags=['admin-auth'])
router.include_router(routes_users.router, prefix='/users', tags=['admin-users'])
router.include_router(routes_family.router, prefix='/users', tags=['admin-family'])
router.include_router(routes_content.router, prefix='/content', tags=['admin-content'])
router.include_router(routes_ai.router, prefix='/ai', tags=['admin-ai'])
router.include_router(routes_safety.router, prefix='/safety', tags=['admin-safety'])
router.include_router(routes_reports.router, prefix='/analytics', tags=['admin-analytics'])
router.include_router(routes_settings.router, prefix='/settings', tags=['admin-settings'])
router.include_router(routes_audit.router, prefix='/audit-logs', tags=['admin-audit'])
