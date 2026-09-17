from dataclasses import dataclass
from uuid import UUID

from app.repositories.attachments import AttachmentStore

# Product limit, shared by Pro and current pre-billing access. Billing gates land in Phase 8.
ACCOUNT_STORAGE_LIMIT_BYTES = 5 * 1024 * 1024 * 1024


class StorageQuotaExceeded(ValueError):
    pass


@dataclass(frozen=True)
class StorageUsage:
    used_bytes: int
    limit_bytes: int = ACCOUNT_STORAGE_LIMIT_BYTES


class StorageQuotaService:
    def __init__(self, attachments: AttachmentStore) -> None:
        self._attachments = attachments

    def usage(self, user_id: UUID) -> StorageUsage:
        return StorageUsage(self._attachments.storage_bytes(user_id))

    def reserve(self, user_id: UUID, file_size: int) -> None:
        # Hold the owner row lock until the pending attachment commits in this transaction.
        self._attachments.lock_owner(user_id)
        if self.usage(user_id).used_bytes + file_size > ACCOUNT_STORAGE_LIMIT_BYTES:
            raise StorageQuotaExceeded(
                "Account storage is full. Delete unused files before uploading."
            )
