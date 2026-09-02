"""Dependency probes for health routes. Keep these boring and explicit."""

import httpx
from redis import Redis
from sqlalchemy import text

from app.config import settings
from app.db import engine


def check_postgres() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc.__class__.__name__)}


def check_redis() -> dict:
    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc.__class__.__name__)}


def check_s3() -> dict:
    """LocalStack exposes /_localstack/health. Real AWS checks come later."""
    url = settings.aws_endpoint_url.rstrip("/") + "/_localstack/health"
    try:
        response = httpx.get(url, timeout=2.0)
        response.raise_for_status()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc.__class__.__name__)}
