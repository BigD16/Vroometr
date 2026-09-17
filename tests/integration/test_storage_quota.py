from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from app.db import engine
from app.models.attachment import Attachment
from app.models.user import User
from app.repositories.attachments import AttachmentRepository
from app.repositories.users import UserRepository
from app.services.storage_quota import ACCOUNT_STORAGE_LIMIT_BYTES, StorageQuotaExceeded
from app.services.uploads import UploadService
from app.services.users import UserService
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.unit.test_uploads import _Storage


def test_concurrent_uploads_reserve_quota_atomically():
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar() == 1
    except Exception:
        pytest.skip("Postgres is not running")
    with Session(engine) as session:
        owner = UserService(UserRepository(session)).create(f"quota_race_{uuid4()}")
        session.flush()
        owner_id = owner.id
        repository = AttachmentRepository(session)
        repository.add(
            Attachment(
                user_id=owner_id,
                s3_key=f"quota/{uuid4()}",
                file_name="existing.pdf",
                file_size=ACCOUNT_STORAGE_LIMIT_BYTES - 128,
                mime_type="application/pdf",
                purpose="document",
                retention_class="persistent",
                status="uploaded",
            )
        )
        session.commit()
    barrier = Barrier(2)

    def attempt():
        with Session(engine) as session:
            user = session.get(User, owner_id)
            service = UploadService(AttachmentRepository(session), _Storage())
            barrier.wait(timeout=10)
            try:
                service.begin(
                    user,
                    file_name="manual.pdf",
                    mime_type="application/pdf",
                    file_size=128,
                    purpose="document",
                )
                session.commit()
                return "reserved"
            except StorageQuotaExceeded:
                session.rollback()
                return "full"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        assert sorted(results) == ["full", "reserved"]
        with Session(engine) as session:
            repository = AttachmentRepository(session)
            assert repository.storage_bytes(owner_id) == ACCOUNT_STORAGE_LIMIT_BYTES
            # Repository quota exclusions also hold on real SQL, independent of test doubles.
            for retention, purpose in [
                ("temporary", "troubleshooting"),
                ("persistent", "garage_scene"),
            ]:
                repository.add(
                    Attachment(
                        user_id=owner_id,
                        s3_key=f"quota/{uuid4()}",
                        file_name="excluded.png",
                        file_size=512,
                        mime_type="image/png",
                        purpose=purpose,
                        retention_class=retention,
                        status="uploaded",
                    )
                )
            assert repository.storage_bytes(owner_id) == ACCOUNT_STORAGE_LIMIT_BYTES
    finally:
        with Session(engine) as session:
            session.delete(session.get(User, owner_id))
            session.commit()
