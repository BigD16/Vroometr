from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.db import engine
from app.models.attachment import Attachment
from app.repositories.attachments import AttachmentRepository
from app.repositories.users import UserRepository
from app.services.users import UserService
from sqlalchemy import text
from sqlalchemy.orm import Session


@pytest.fixture
def db_session() -> Iterator[Session]:
    try:
        connection = engine.connect()
    except Exception:
        pytest.skip("Postgres is not running")

    transaction = connection.begin()
    exists = connection.execute(text("SELECT to_regclass('public.attachments')")).scalar()
    if exists is None:
        transaction.rollback()
        connection.close()
        pytest.skip("Run `cd services/api && alembic upgrade head` first")

    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_attachment_round_trip_is_owner_scoped(db_session: Session) -> None:
    users = UserService(UserRepository(db_session))
    owner = users.create("user_clerk_attachment_db_owner")
    other = users.create("user_clerk_attachment_db_other")
    db_session.flush()
    now = datetime.now(UTC)
    attachment = Attachment(
        user_id=owner.id,
        s3_key=f"users/{owner.id}/attachments/test.pdf",
        file_name="test.pdf",
        mime_type="application/pdf",
        file_size=128,
        purpose="document",
        status="pending",
        retention_class="persistent",
        created_at=now,
        updated_at=now,
    )
    repository = AttachmentRepository(db_session)

    created = repository.add(attachment)
    assert repository.get(created.id, owner.id) is created
    assert repository.get(created.id, other.id) is None

    created.status = "uploaded"
    repository.save(created)
    db_session.expire(created)
    assert repository.get(created.id, owner.id).status == "uploaded"
