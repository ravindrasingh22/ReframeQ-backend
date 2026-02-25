from fastapi import APIRouter

from app.api.admin.router import router as admin_router
from app.api.app_api.router import router as app_router

router = APIRouter(prefix='/api')
router.include_router(app_router, prefix='/app', tags=['app'])
router.include_router(admin_router, prefix='/admin', tags=['admin'])
