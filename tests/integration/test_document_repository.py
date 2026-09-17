from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.db import engine
from app.models.attachment import Attachment
from app.models.document import Document
from app.repositories.attachments import AttachmentRepository
from app.repositories.bikes import BikeRepository
from app.repositories.documents import DocumentRepository
from app.repositories.users import UserRepository
from app.services.bikes import BikeService
from app.services.documents import DocumentService
from app.services.users import UserService
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.unit.test_documents import META, Inspector


@pytest.fixture
def document_session():
    try:
        connection = engine.connect()
    except Exception:
        pytest.skip("Postgres is not running")
    transaction = connection.begin()
    if connection.execute(text("SELECT to_regclass('public.documents')")).scalar() is None:
        transaction.rollback()
        connection.close()
        pytest.skip("Apply migration 0010_documents first")
    with Session(bind=connection) as session:
        yield session
    transaction.rollback()
    connection.close()


def test_versions_primary_constraint_and_file_deletion(document_session):
    session = document_session
    users = UserService(UserRepository(session))
    owner = users.create(f"documents_owner_{uuid4()}")
    other = users.create(f"documents_other_{uuid4()}")
    bikes = BikeRepository(session)
    bike = BikeService(bikes).create(
        owner,
        nickname="Test",
        make="Test",
        model="Test",
        year=2024,
        bike_type="dirt_bike",
        powertrain_type="electric",
    )
    attachments = AttachmentRepository(session)
    repository = DocumentRepository(session)
    service = DocumentService(repository, attachments, bikes, Inspector())
    files = [
        attachments.add(
            Attachment(
                user_id=owner.id,
                s3_key=f"document-test/{uuid4()}",
                file_name="manual.pdf",
                file_size=128,
                mime_type="application/pdf",
                status="uploaded",
                purpose="document",
                retention_class="persistent",
            )
        )
        for _ in range(2)
    ]
    first = service.register(
        owner, bike_id=bike.id, attachment_id=files[0].id, metadata=META
    ).document
    service.confirm(owner, first.id, META)
    second = service.register(
        owner,
        bike_id=bike.id,
        attachment_id=files[1].id,
        metadata=META,
        supersedes_document_id=first.id,
    ).document
    service.confirm(owner, second.id, META)
    session.expire_all()
    assert repository.get(first.id, other.id) is None
    assert repository.get(first.id, owner.id).status == "archived"
    assert repository.get(second.id, owner.id).is_primary
    assert first.file_hash == second.file_hash
    assert first.revision == 1 and second.revision == 2
    assert first.version_group_id == second.version_group_id
    with pytest.raises(IntegrityError), session.begin_nested():
        first.status = "active"
        first.is_primary = True
        session.flush()
    session.expire_all()
    service.select_primary(owner, first.id)
    assert first.is_primary and not second.is_primary
    deleted_document_id = first.id
    attachments.delete(files[0])
    session.expire_all()
    assert repository.get(deleted_document_id, owner.id) is None
    assert repository.get(second.id, owner.id).supersedes_document_id is None
    assert repository.get(second.id, owner.id).revision == 2


def test_primary_requires_confirmed_manufacturer_manual(document_session):
    session = document_session
    owner = UserService(UserRepository(session)).create(f"primary_constraint_{uuid4()}")
    bikes = BikeRepository(session)
    bike = BikeService(bikes).create(
        owner,
        nickname="Test",
        make="Test",
        model="Test",
        year=2024,
        bike_type="motorcycle",
        powertrain_type="electric",
    )
    file = AttachmentRepository(session).add(
        Attachment(
            user_id=owner.id,
            s3_key=f"document-test/{uuid4()}",
            file_name="test.pdf",
            file_size=1,
            mime_type="application/pdf",
            purpose="document",
            status="uploaded",
            retention_class="persistent",
        )
    )
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            Document(
                bike_id=bike.id,
                attachment_id=file.id,
                document_type="supporting_document",
                make="Test",
                model="Test",
                year=2024,
                file_hash="a" * 64,
                status="active",
                is_primary=True,
                confirmed_at=datetime.now(UTC),
            )
        )
        session.flush()
