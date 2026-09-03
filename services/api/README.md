# FastAPI backend

```text
routes/        HTTP only (validate, identify, call a service, return JSON)
services/      business rules (users, age gate, bikes)
repositories/  database access (users, parental_consents, bikes)
auth/          Clerk JWT + webhook signature checks
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
- Current user (Clerk session): http://localhost:8000/v1/me
- Age eligibility: `GET /v1/me/eligibility`, `POST /v1/me/date-of-birth`, `POST /v1/parental-consents`
- Bikes (signed-in owner only): `GET/POST /v1/bikes`, `GET/PATCH /v1/bikes/{id}`
- Clerk webhook: `POST /v1/webhooks/clerk`

## If you want to change…

| Change | File |
| --- | --- |
| Ports / DB password | repo-root `.env` |
| How env is read | `libs/vroometr/settings.py` (values in `.env`) |
| Health checks | `app/health_checks.py` and `app/routes/health.py` |
| Error JSON shape | `app/errors.py` |
| Tables | new SQLAlchemy models + a new Alembic revision (`app/models/`) |
| Users / roles / entitlements | `app/models/user.py`, `app/services/users.py` |
| Clerk session / `/v1/me` | `app/auth/tokens.py`, `app/deps.py`, `app/routes/me.py` |
| Clerk webhook | `app/auth/webhooks.py`, `app/routes/clerk_webhooks.py` |
| Age gate / parental consent | `app/services/age_gate.py`, `app/routes/age_gate.py` |
| Bikes / garage machine rows | `app/models/bike.py`, `app/services/bikes.py`, `app/routes/bikes.py` |
| A new HTTP endpoint | `app/routes/` (keep logic out of the route) |
