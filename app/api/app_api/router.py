from fastapi import APIRouter

from app.api.app_api import (
    routes_auth,
    routes_chat,
    routes_dashboard,
    routes_family,
    routes_moods,
    routes_onboarding,
    routes_onboarding_ai,
    routes_profile,
)

router = APIRouter()
router.include_router(routes_auth.router, prefix='/auth', tags=['app-auth'])
router.include_router(routes_profile.router, prefix='/profile', tags=['app-profile'])
router.include_router(routes_dashboard.router, prefix='/dashboard', tags=['app-dashboard'])
router.include_router(routes_moods.router, prefix='/moods', tags=['app-moods'])
router.include_router(routes_family.router, prefix='/family', tags=['app-family'])
router.include_router(routes_chat.router, prefix='/chat', tags=['app-chat'])
router.include_router(routes_onboarding.router, prefix='/onboarding', tags=['app-onboarding'])
router.include_router(routes_onboarding_ai.router, prefix='/onboarding/ai', tags=['app-onboarding-ai'])
