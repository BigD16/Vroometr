from uuid import uuid4

import pytest
from app.models.bike import Bike
from app.models.user import User
from app.services.conversations import (
    ConversationNotFound,
    ConversationService,
    InvalidConversation,
    compress_rolling_summary,
)
from tests.unit.fakes import InMemoryBikeRepository


class Conversations:
    def __init__(self):
        self.items = {}
        self.messages = {}
        self.boundaries = {}

    def get(self, conversation_id, user_id):
        conversation = self.items.get(conversation_id)
        return conversation if conversation and conversation.user_id == user_id else None

    def list_for_user(self, user_id, *, bike_id=None):
        items = [item for item in self.items.values() if item.user_id == user_id]
        if bike_id is not None:
            items = [
                item
                for item in items
                if item.current_bike_id == bike_id or item.initial_bike_id == bike_id
            ]
        return sorted(items, key=lambda item: item.updated_at, reverse=True)

    def add(self, conversation):
        if conversation.id is None:
            conversation.id = uuid4()
        self.items[conversation.id] = conversation
        self.messages.setdefault(conversation.id, [])
        self.boundaries.setdefault(conversation.id, [])
        return conversation

    save = add

    def delete(self, conversation):
        self.items.pop(conversation.id, None)
        self.messages.pop(conversation.id, None)
        self.boundaries.pop(conversation.id, None)

    def list_messages(self, conversation_id):
        return list(self.messages.get(conversation_id, []))

    def add_message(self, message):
        if message.id is None:
            message.id = uuid4()
        self.messages.setdefault(message.conversation_id, []).append(message)
        return message

    def latest_message(self, conversation_id):
        items = self.messages.get(conversation_id, [])
        return items[-1] if items else None

    def list_boundaries(self, conversation_id):
        return list(self.boundaries.get(conversation_id, []))

    def add_boundary(self, boundary):
        if boundary.id is None:
            boundary.id = uuid4()
        self.boundaries.setdefault(boundary.conversation_id, []).append(boundary)
        return boundary


def setup_conversations():
    owner, other = User(id=uuid4()), User(id=uuid4())
    bikes = InMemoryBikeRepository()
    bike = bikes.add(Bike(user_id=owner.id))
    second = bikes.add(Bike(user_id=owner.id, nickname="Second"))
    foreign = bikes.add(Bike(user_id=other.id))
    store = Conversations()
    service = ConversationService(store, bikes)
    return owner, other, bike, second, foreign, store, service


def test_create_list_and_owner_isolation():
    owner, other, bike, _, foreign, store, service = setup_conversations()
    conversation = service.create(owner, bike.id)
    assert conversation.initial_bike_id == bike.id
    assert conversation.current_bike_id == bike.id
    assert len(service.list(owner, bike.id)) == 1
    with pytest.raises(ConversationNotFound):
        service.create(owner, foreign.id)
    with pytest.raises(ConversationNotFound):
        service.list(other, bike.id)
    with pytest.raises(ConversationNotFound):
        service.get(other, conversation.id)
    assert store.get(conversation.id, other.id) is None


def test_append_stamps_bike_context_and_refreshes_summary():
    owner, _, bike, second, _, _, service = setup_conversations()
    conversation = service.create(owner, bike.id)
    with pytest.raises(InvalidConversation):
        service.append_message(owner, conversation.id, "   ")
    message = service.append_message(owner, conversation.id, "oil change interval?")
    assert message.role == "user"
    assert message.bike_context_id == bike.id
    detail = service.get(owner, conversation.id)
    assert detail.conversation.rolling_summary == "user: oil change interval?"
    assert detail.conversation.summary_model_version == "deterministic-v1"
    service.switch_bike(owner, conversation.id, second.id)
    switched = service.append_message(owner, conversation.id, "for the second bike")
    assert switched.bike_context_id == second.id


def test_switch_bike_records_boundary_and_rejects_foreign_bikes():
    owner, other, bike, second, foreign, store, service = setup_conversations()
    conversation = service.create(owner, bike.id)
    first = service.append_message(owner, conversation.id, "hello")
    detail = service.switch_bike(owner, conversation.id, second.id)
    assert detail.conversation.current_bike_id == second.id
    assert len(detail.boundaries) == 1
    assert detail.boundaries[0].from_bike_id == bike.id
    assert detail.boundaries[0].to_bike_id == second.id
    assert detail.boundaries[0].message_id == first.id
    same = service.switch_bike(owner, conversation.id, second.id)
    assert len(same.boundaries) == 1
    with pytest.raises(ConversationNotFound):
        service.switch_bike(owner, conversation.id, foreign.id)
    with pytest.raises(ConversationNotFound):
        service.switch_bike(other, conversation.id, second.id)
    assert len(store.boundaries[conversation.id]) == 1


def test_delete_removes_messages_and_boundaries():
    owner, other, bike, second, _, store, service = setup_conversations()
    conversation = service.create(owner, bike.id)
    service.append_message(owner, conversation.id, "keep me briefly")
    service.switch_bike(owner, conversation.id, second.id)
    with pytest.raises(ConversationNotFound):
        service.delete(other, conversation.id)
    service.delete(owner, conversation.id)
    assert conversation.id not in store.items
    assert conversation.id not in store.messages
    assert conversation.id not in store.boundaries
    with pytest.raises(ConversationNotFound):
        service.get(owner, conversation.id)


def test_compress_rolling_summary_bounds_length():
    from app.models.conversation import ConversationMessage

    messages = [
        ConversationMessage(
            role="user",
            content="x" * 300,
            bike_context_id=uuid4(),
            conversation_id=uuid4(),
        )
        for _ in range(12)
    ]
    summary = compress_rolling_summary(messages)
    assert summary is not None
    assert len(summary) == 2000
