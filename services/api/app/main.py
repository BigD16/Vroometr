from fastapi import FastAPI

from app.errors import AppError, app_error_handler
from app.routes.age_gate import router as age_gate_router
from app.routes.bikes import router as bikes_router
from app.routes.clerk_webhooks import router as clerk_webhook_router
from app.routes.health import router as health_router
from app.routes.me import router as me_router


def create_app() -> FastAPI:
    app = FastAPI(title="Vroometr API", version="0.1.0")
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(health_router)
    app.include_router(me_router)
    app.include_router(age_gate_router)
    app.include_router(bikes_router)
    app.include_router(clerk_webhook_router)
    return app


app = create_app()
