from fastapi import APIRouter

from app.api.app_api import routes_auth, routes_moods, routes_profile

router = APIRouter()
router.include_router(routes_auth.router, prefix='/auth', tags=['app-auth'])
router.include_router(routes_profile.router, prefix='/profile', tags=['app-profile'])
router.include_router(routes_moods.router, prefix='/moods', tags=['app-moods'])
