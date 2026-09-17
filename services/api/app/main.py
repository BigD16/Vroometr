from fastapi import FastAPI

from app.errors import AppError, app_error_handler
from app.routes.active_bike import router as active_bike_router
from app.routes.age_gate import router as age_gate_router
from app.routes.attachment_links import router as attachment_links_router
from app.routes.attachment_processing import router as attachment_processing_router
from app.routes.attachments import router as attachments_router
from app.routes.bikes import router as bikes_router
from app.routes.clerk_webhooks import router as clerk_webhook_router
from app.routes.document_index import router as document_index_router
from app.routes.document_ingestion import router as document_ingestion_router
from app.routes.documents import router as documents_router
from app.routes.health import router as health_router
from app.routes.me import router as me_router
from app.routes.retrieval import router as retrieval_router
from app.routes.uploads import router as uploads_router


def create_app() -> FastAPI:
    app = FastAPI(title="Vroometr API", version="0.1.0")
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(health_router)
    app.include_router(me_router)
    app.include_router(age_gate_router)
    app.include_router(bikes_router)
    app.include_router(active_bike_router)
    app.include_router(uploads_router)
    app.include_router(attachment_links_router)
    app.include_router(attachments_router)
    app.include_router(documents_router)
    app.include_router(document_ingestion_router)
    app.include_router(document_index_router)
    app.include_router(retrieval_router)
    app.include_router(attachment_processing_router)
    app.include_router(clerk_webhook_router)
    return app


app = create_app()
