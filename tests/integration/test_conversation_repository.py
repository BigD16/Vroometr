from uuid import uuid4

import pytest
from app.db import engine
from app.repositories.bikes import BikeRepository
from app.repositories.conversations import ConversationRepository
from app.repositories.users import UserRepository
from app.services.bikes import BikeService
from app.services.conversations import ConversationService
from app.services.users import UserService
from sqlalchemy import text
from sqlalchemy.orm import Session


@pytest.fixture
def conversation_session():
    try:
        connection = engine.connect()
    except Exception:
        pytest.skip("Postgres is not running")
    transaction = connection.begin()
    if connection.execute(text("SELECT to_regclass('public.conversations')")).scalar() is None:
        transaction.rollback()
        connection.close()
        pytest.skip("Apply migration 0014_conversations first")
    with Session(bind=connection) as session:
        yield session
    transaction.rollback()
    connection.close()


def test_conversation_repository_boundaries_and_delete(conversation_session):
    session = conversation_session
    users = UserService(UserRepository(session))
    owner = users.create(f"conversations_owner_{uuid4()}")
    bikes = BikeRepository(session)
    bike_service = BikeService(bikes)
    bike = bike_service.create(
        owner,
        nickname="Primary",
        make="Test",
        model="One",
        year=2024,
        bike_type="dirt_bike",
        powertrain_type="electric",
    )
    second = bike_service.create(
        owner,
        nickname="Secondary",
        make="Test",
        model="Two",
        year=2023,
        bike_type="dirt_bike",
        powertrain_type="electric",
    )
    service = ConversationService(ConversationRepository(session), bikes)
    conversation = service.create(owner, bike.id)
    message = service.append_message(owner, conversation.id, "check valve clearance")
    detail = service.switch_bike(owner, conversation.id, second.id)
    assert detail.conversation.current_bike_id == second.id
    assert detail.boundaries[0].message_id == message.id
    listed = service.list(owner, bike_id=bike.id)
    assert [item.id for item in listed] == [conversation.id]
    listed_current = service.list(owner, bike_id=second.id)
    assert [item.id for item in listed_current] == [conversation.id]
    service.delete(owner, conversation.id)
    session.flush()
    assert (
        session.execute(
            text("SELECT count(*) FROM conversations WHERE id = :id"),
            {"id": conversation.id},
        ).scalar()
        == 0
    )
    assert (
        session.execute(
            text("SELECT count(*) FROM conversation_messages WHERE conversation_id = :id"),
            {"id": conversation.id},
        ).scalar()
        == 0
    )
    assert (
        session.execute(
            text(
                "SELECT count(*) FROM conversation_context_boundaries WHERE conversation_id = :id"
            ),
            {"id": conversation.id},
        ).scalar()
        == 0
    )
