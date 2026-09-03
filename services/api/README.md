# FastAPI backend

```text
routes/        HTTP only (validation, auth later, call a service, return JSON)
services/      business rules (users live here; Clerk comes next)
repositories/  database access (users table)
```

Migrations are explicit (`alembic upgrade head`). The app does **not** migrate on startup.

## Run

From the repo root, with Compose already up:

```bash
source .venv/bin/activate
cd services/api
alembic upgrade head
cd ../..
./scripts/api-dev.sh
```

- Liveness: http://localhost:8000/health/live
- Readiness: http://localhost:8000/health/ready (needs Postgres)
- Dependencies: http://localhost:8000/health/deps (Postgres, Redis, LocalStack)

## If you want to change…

| Change | File |
| --- | --- |
| Ports / DB password | repo-root `.env` |
| How env is read | `libs/vroometr/settings.py` (values in `.env`) |
| Health checks | `app/health_checks.py` and `app/routes/health.py` |
| Error JSON shape | `app/errors.py` |
| Tables | new SQLAlchemy models + a new Alembic revision (`app/models/`) |
| Users / roles / entitlements | `app/models/user.py`, `app/services/users.py` |
| A new HTTP endpoint | `app/routes/` (keep logic out of the route) |
