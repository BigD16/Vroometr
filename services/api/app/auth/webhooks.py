import json
from typing import Protocol

from svix.webhooks import Webhook, WebhookVerificationError


class InvalidWebhook(Exception):
    """Clerk webhook signature is missing or invalid."""


class WebhookVerifier(Protocol):
    def verify(self, payload: bytes, headers: dict[str, str]) -> dict: ...


class ClerkWebhookVerifier:
    def __init__(self, secret: str) -> None:
        self._secret = secret

    def verify(self, payload: bytes, headers: dict[str, str]) -> dict:
        if not self._secret:
            raise InvalidWebhook("Clerk webhook secret is not configured")
        svix_headers = {
            "svix-id": headers.get("svix-id") or headers.get("Svix-Id") or "",
            "svix-timestamp": headers.get("svix-timestamp")
            or headers.get("Svix-Timestamp")
            or "",
            "svix-signature": headers.get("svix-signature")
            or headers.get("Svix-Signature")
            or "",
        }
        try:
            Webhook(self._secret).verify(payload, svix_headers)
        except WebhookVerificationError as exc:
            raise InvalidWebhook("invalid Clerk webhook signature") from exc
        try:
            body = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise InvalidWebhook("webhook payload is not JSON") from exc
        if not isinstance(body, dict):
            raise InvalidWebhook("webhook payload is not an object")
        return body
