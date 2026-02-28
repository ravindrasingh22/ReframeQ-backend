from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router as api_router
from app.core.config import settings
from app.db.init_db import init_db

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:4173',
        'http://127.0.0.1:4173',
        'http://localhost:8081',
        'http://127.0.0.1:8081',
        'http://localhost:19006',
        'http://127.0.0.1:19006',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(api_router)


@app.on_event('startup')
def on_startup() -> None:
    init_db()


@app.get('/health', tags=['system'])
def healthcheck() -> dict[str, str]:
    return {'status': 'ok'}
