from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.health_checks import check_postgres, check_redis, check_s3

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict:
    """Process is running. Does not check other services."""
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> JSONResponse:
    """Can serve traffic — Postgres must be reachable."""
    postgres = check_postgres()
    if postgres["status"] != "ok":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "postgres": postgres},
        )
    return JSONResponse(content={"status": "ok"})


@router.get("/health/deps")
def deps() -> JSONResponse:
    """Postgres, Redis, and S3/LocalStack each reported separately."""
    payload = {
        "postgres": check_postgres(),
        "redis": check_redis(),
        "s3": check_s3(),
    }
    all_ok = all(item["status"] == "ok" for item in payload.values())
    code = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=payload)
