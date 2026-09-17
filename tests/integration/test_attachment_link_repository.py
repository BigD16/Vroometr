from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.db import engine
from app.models.attachment import Attachment
from app.models.attachment_link import AttachmentLink
from app.repositories.attachment_links import AttachmentLinkRepository
from app.repositories.attachments import AttachmentRepository
from app.repositories.users import UserRepository
from app.services.users import UserService
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session


@pytest.fixture
def db_session() -> Iterator[Session]:
    try:
        connection = engine.connect()
    except Exception:
        pytest.skip("Postgres is not running")
    transaction = connection.begin()
    if connection.execute(text("SELECT to_regclass('public.attachment_links')")).scalar() is None:
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


def test_many_to_many_retry_owner_scope_and_cascade(db_session):
    users = UserService(UserRepository(db_session))
    owner = users.create(f"attachment_links_owner_{uuid4()}")
    other = users.create(f"attachment_links_other_{uuid4()}")
    attachments = AttachmentRepository(db_session)
    files = [
        attachments.add(
            Attachment(
                user_id=owner.id,
                s3_key=f"test/{uuid4()}.pdf",
                file_name="receipt.pdf",
                mime_type="application/pdf",
                file_size=128,
                purpose="document",
                status="uploaded",
                retention_class="persistent",
            )
        )
        for _ in range(2)
    ]
    repository = AttachmentLinkRepository(db_session)
    maintenance_id, modification_id = uuid4(), uuid4()

    def add(attachment, entity_type, entity_id):
        return repository.add(
            AttachmentLink(
                id=uuid4(),
                attachment_id=attachment.id,
                entity_type=entity_type,
                entity_id=entity_id,
                relationship_type="evidence",
                created_at=datetime.now(UTC),
            )
        )

    # Storage supports future domains; service endpoints still require implemented ownership checks.
    first = add(files[0], "maintenance_record", maintenance_id)
    assert add(files[0], "maintenance_record", maintenance_id).id == first.id
    second = add(files[0], "modification", modification_id)
    third = add(files[1], "maintenance_record", maintenance_id)
    assert repository.get(first.id, owner.id).id == first.id
    assert repository.get(first.id, other.id) is None
    assert repository.list_for_entity("maintenance_record", maintenance_id, other.id) == []
    assert {
        link.id
        for link in repository.list_for_entity(
            "maintenance_record",
            maintenance_id,
            owner.id,
        )
    } == {first.id, third.id}

    repository.delete(first)
    assert repository.get(first.id, owner.id) is None
    assert repository.get(second.id, owner.id) is not None
    assert attachments.get(files[0].id, owner.id) is not None

    db_session.delete(files[0])
    db_session.flush()
    assert repository.get(second.id, owner.id) is None
    assert repository.get(third.id, owner.id) is not None
    count = db_session.scalar(
        select(func.count())
        .select_from(AttachmentLink)
        .where(
            AttachmentLink.attachment_id == files[0].id,
        )
    )
    assert count == 0
