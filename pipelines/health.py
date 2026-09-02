"""Health pipeline. Celery calls process(); this file owns the work."""


def process() -> dict:
    return {"status": "ok"}
