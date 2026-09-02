# Infra

Local data stores. No API or website containers yet.

| Service    | What it is              |
| ---------- | ----------------------- |
| Postgres   | Database + pgvector     |
| Redis      | Celery broker           |
| LocalStack | Fake AWS — S3 only      |
| Unleash    | Feature flags (OpenFeature provider) |

Ports and passwords: `.env` only. [`.env.example`](../.env.example) lists the key names.

S3 bucket created on first start: `S3_BUCKET`. Unleash database: `UNLEASH_DATABASE_NAME` (created on first Postgres boot, or by `scripts/ensure-unleash-db.sh` after `./scripts/dev-up.sh`).

Unleash UI: `http://localhost:${UNLEASH_PORT}` (admin password is `UNLEASH_ADMIN_PASSWORD`). The API uses OpenFeature; it does not call Unleash APIs directly.

## Commands

From the repo root:

```bash
./scripts/dev-up.sh
./scripts/dev-down.sh
```

Requires a filled-in `.env` (copy [`.env.example`](../.env.example) and set every value). Compose reads `.env` only.

```bash
./scripts/compose.sh ps
```

## If you want to change…

| Change | File |
| --- | --- |
| Ports, passwords, bucket name, region | [`.env`](../.env) (start from [`.env.example`](../.env.example)) |
| Which services / images | [`docker-compose.yml`](docker-compose.yml) |
| Postgres extensions | [`postgres/init.sql`](postgres/init.sql) |
| Unleash database on first Postgres boot | [`postgres/create-unleash-db.sh`](postgres/create-unleash-db.sh) |
| How the S3 bucket is created | [`localstack/ready.d/create-s3-bucket.sh`](localstack/ready.d/create-s3-bucket.sh) |
| Unleash database on an old volume | [`../scripts/ensure-unleash-db.sh`](../scripts/ensure-unleash-db.sh) |

Postgres `init.sql` only runs on an empty volume. If you already started Compose once, either `docker compose -f infra/docker-compose.yml down -v` (wipes local data) or enable the extension by hand.
