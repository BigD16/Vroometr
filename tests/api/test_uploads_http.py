from uuid import UUID

from app.auth.tokens import InvalidIdentity
from app.deps import get_token_verifier, get_upload_service, get_user_service
from app.main import create_app
from app.models.attachment import Attachment
from app.services.uploads import (
    PresignedPost,
    StoredObjectMetadata,
    StoredObjectNotFound,
    UploadService,
)
from app.services.users import UserService
from fastapi.testclient import TestClient
from tests.unit.fakes import InMemoryUserRepository


class _FakeTokens:
    def clerk_user_id(self, token: str) -> str:
        if token == "good-token":
            return "user_clerk_upload"
        if token == "other-token":
            return "user_clerk_upload_other"
        raise InvalidIdentity("bad token")


class _Attachments:
    def __init__(self) -> None:
        self.items: dict[UUID, Attachment] = {}

    def lock_owner(self, user_id: UUID) -> None:
        pass

    def storage_bytes(self, user_id: UUID) -> int:
        return sum(a.file_size for a in self.items.values() if a.user_id == user_id
                   and a.retention_class == "persistent" and a.purpose != "garage_scene")

    def list_for_user(self, user_id: UUID) -> list[Attachment]:
        return [a for a in self.items.values() if a.user_id == user_id]

    def delete(self, attachment: Attachment) -> None:
        del self.items[attachment.id]

    def get(self, attachment_id: UUID, user_id: UUID) -> Attachment | None:
        attachment = self.items.get(attachment_id)
        if attachment is None or attachment.user_id != user_id:
            return None
        return attachment

    def add(self, attachment: Attachment) -> Attachment:
        self.items[attachment.id] = attachment
        return attachment

    def save(self, attachment: Attachment) -> Attachment:
        self.items[attachment.id] = attachment
        return attachment


class _Storage:
    def __init__(self) -> None:
        self.objects: dict[str, StoredObjectMetadata] = {}

    def presign_post(self, **kwargs) -> PresignedPost:
        return PresignedPost(
            url="http://localhost:4566/vroometr",
            fields={
                "key": kwargs["object_key"],
                "policy": "signed",
            },
            expires_in=kwargs["expires_in"],
        )

    def head_object(self, object_key: str) -> StoredObjectMetadata:
        try:
            return self.objects[object_key]
        except KeyError as exc:
            raise StoredObjectNotFound from exc


def _client() -> tuple[TestClient, _Attachments, _Storage]:
    users = InMemoryUserRepository()
    attachments = _Attachments()
    storage = _Storage()
    uploads = UploadService(attachments, storage)
    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: _FakeTokens()
    app.dependency_overrides[get_user_service] = lambda: UserService(users)
    app.dependency_overrides[get_upload_service] = lambda: uploads
    return TestClient(app), attachments, storage


def _auth(token: str = "good-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _presign(client: TestClient, token: str = "good-token"):
    return client.post(
        "/v1/uploads/presign",
        json={
            "file_name": "manual.pdf",
            "mime_type": "application/pdf",
            "file_size": 128,
            "purpose": "document",
        },
        headers=_auth(token),
    )


def test_upload_routes_require_sign_in() -> None:
    client, _, _ = _client()
    assert _presign(client, token="bad-token").status_code == 401
    assert (
        client.post(
            "/v1/uploads/00000000-0000-0000-0000-000000000001/complete"
        ).status_code
        == 401
    )


def test_presign_returns_only_browser_upload_material() -> None:
    client, attachments, _ = _client()
    response = _presign(client)
    assert response.status_code == 200
    body = response.json()
    attachment = attachments.items[UUID(body["attachment_id"])]
    assert body["method"] == "POST"
    assert body["url"] == "http://localhost:4566/vroometr"
    assert body["object_key"] == attachment.s3_key
    assert body["expires_in"] == 900
    assert "aws_secret_access_key" not in response.text.lower()
    assert attachment.status == "pending"


def test_invalid_metadata_is_rejected_before_presign() -> None:
    client, attachments, _ = _client()
    response = client.post(
        "/v1/uploads/presign",
        json={
            "file_name": "malware.exe",
            "mime_type": "application/octet-stream",
            "file_size": 10,
        },
        headers=_auth(),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_upload"
    assert attachments.items == {}


def test_complete_verifies_object_and_is_owner_scoped() -> None:
    client, attachments, storage = _client()
    presigned = _presign(client).json()
    attachment_id = UUID(presigned["attachment_id"])
    attachment = attachments.items[attachment_id]

    incomplete = client.post(
        f"/v1/uploads/{attachment_id}/complete",
        headers=_auth(),
    )
    assert incomplete.status_code == 409
    assert incomplete.json()["error"]["code"] == "upload_incomplete"

    storage.objects[attachment.s3_key] = StoredObjectMetadata(
        content_length=attachment.file_size,
        content_type=attachment.mime_type,
        attachment_id=str(attachment.id),
    )
    hidden = client.post(
        f"/v1/uploads/{attachment_id}/complete",
        headers=_auth("other-token"),
    )
    assert hidden.status_code == 404

    completed = client.post(
        f"/v1/uploads/{attachment_id}/complete",
        headers=_auth(),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "uploaded"
