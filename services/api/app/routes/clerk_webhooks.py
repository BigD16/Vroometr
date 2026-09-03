from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.webhooks import InvalidWebhook, WebhookVerifier
from app.deps import get_clerk_webhook_verifier, get_user_service
from app.errors import AppError
from app.services.clerk_sync import ClerkSyncService
from app.services.users import UserService

router = APIRouter(tags=["webhooks"])


@router.post("/v1/webhooks/clerk")
async def clerk_webhook(
    request: Request,
    verifier: Annotated[WebhookVerifier, Depends(get_clerk_webhook_verifier)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> dict:
    payload = await request.body()
    headers = {key: value for key, value in request.headers.items()}
    try:
        event = verifier.verify(payload, headers)
    except InvalidWebhook as exc:
        raise AppError("invalid_webhook", "Invalid Clerk webhook signature", 400) from exc
    event_type = event.get("type")
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    clerk_user_id = data.get("id") if isinstance(data, dict) else None
    if not isinstance(event_type, str) or not event_type:
        raise AppError("invalid_webhook", "Missing event type", 400)
    if event_type in {"user.created", "user.updated"}:
        if not isinstance(clerk_user_id, str) or not clerk_user_id.strip():
            raise AppError("invalid_webhook", "Missing Clerk user id", 400)
        ClerkSyncService(user_service).apply(event_type, clerk_user_id)
    return {"status": "ok"}
