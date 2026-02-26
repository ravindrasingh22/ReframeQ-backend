# ReframeQ Backend

FastAPI API layer with explicit router segregation:
- App APIs: `/api/app/*` for mobile app users (`app_user` token required)
- Admin APIs: `/api/admin/*` for admin/staff users (`admin`/`staff` token required)

## Stack
- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy + Alembic
- PostgreSQL (via `psycopg`)
- Redis + Celery
- JWT auth (`python-jose`)

## Setup
1. Create virtual environment and install deps:
   - `python3.11 -m venv .venv && source .venv/bin/activate`
   - `pip install -e .`
2. Copy env file:
   - `cp .env.example .env`
3. Run API:
   - `uvicorn app.main:app --reload`

## Docker Compose
1. Create env file:
   - `cp .env.example .env`
2. Start API + Postgres + Redis + Celery worker:
   - `docker compose up --build`
3. API endpoints:
   - API base: `http://localhost:8000`
   - Docs: `http://localhost:8000/docs`

Notes:
- In compose, `DATABASE_URL` and `REDIS_URL` are overridden to use `db` and `redis` service hosts.
- Source is mounted into containers for dev iteration.

## Security Model
- `app/api/app_api/*` routes depend on `get_current_app_user`
- `app/api/admin/*` routes depend on `get_current_admin_user`
- Token issuers are separate:
  - App login: `POST /api/app/auth/login`
  - Admin login: `POST /api/admin/auth/login`

## Celery
- Worker app: `app/workers/celery_app.py`
- Start worker:
  - `celery -A app.workers.celery_app.celery_app worker --loglevel=info`

## RBAC (Admin v1)
Roles:
- `admin`: full access across all admin modules
- `content_editor`: content library only
- `support`: user issues + limited user metadata
- `analyst`: analytics only

Permissions:
- `users.read_limited`, `users.manage_issues`
- `content.read`, `content.write`
- `ai.read`, `ai.write`
- `safety.read`, `safety.write`
- `analytics.read`
- `audit.read`
- `app.use`

Role mapping is defined in `app/core/rbac.py`.
All protected endpoints use explicit permission dependencies from `app/api/deps.py`.

## Seed Development Data
- Start dependencies:
  - `docker compose up -d db redis`
- Run seed job:
  - `docker compose run --rm seed`
- Start API + worker:
  - `docker compose up api worker`
