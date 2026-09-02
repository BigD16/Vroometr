# Infra

Local data stores. No API or website containers yet.

| Service    | Port | What it is              |
| ---------- | ---- | ----------------------- |
| Postgres   | 5432 | Database + pgvector     |
| Redis      | 6379 | Celery broker (later)   |
| LocalStack | 4566 | Fake AWS — S3 only      |

S3 bucket created on first start: whatever `S3_BUCKET` is in `.env` (default `vroometr-dev`)

## Commands

From the repo root:

```bash
./scripts/dev-up.sh
./scripts/dev-down.sh
```

That copies `.env.example` → `.env` if you do not have a `.env` yet, then runs Compose with `--env-file .env`.

```bash
./scripts/compose.sh ps
```

## If you want to change…

| Change | File |
| --- | --- |
| Ports, passwords, bucket name, region | [`.env`](../.env) (start from [`.env.example`](../.env.example)) |
| Which services / images | [`docker-compose.yml`](docker-compose.yml) |
| Postgres extensions | [`postgres/init.sql`](postgres/init.sql) |
| How the S3 bucket is created | [`localstack/ready.d/create-s3-bucket.sh`](localstack/ready.d/create-s3-bucket.sh) |

Postgres `init.sql` only runs on an empty volume. If you already started Compose once, either `docker compose -f infra/docker-compose.yml down -v` (wipes local data) or enable the extension by hand.
