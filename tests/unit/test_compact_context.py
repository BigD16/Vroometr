from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.models.bike import Bike
from app.models.conversation import ConversationMessage
from app.models.user import User
from app.services.compact_context import (
    COMPACT_CONTEXT_VERSION,
    CompactContextService,
    select_recent_turns,
)
from app.services.conversations import ConversationNotFound, ConversationService
from tests.unit.fakes import InMemoryBikeRepository
from tests.unit.test_conversations import Conversations


def _bike(user_id, **kwargs):
    defaults = dict(
        user_id=user_id,
        nickname="Trail",
        make="Yamaha",
        model="YZ250F",
        year=2024,
        bike_type="dirt_bike",
        powertrain_type="combustion",
        displacement=250,
        stroke_type="4T",
        current_engine_hours=12.5,
        current_engine_hours_is_estimated=True,
        status="active",
        unit_preference="metric",
    )
    defaults.update(kwargs)
    return Bike(**defaults)


def setup_context():
    owner, other = User(id=uuid4()), User(id=uuid4())
    bikes = InMemoryBikeRepository()
    bike = bikes.add(_bike(owner.id))
    second = bikes.add(_bike(owner.id, nickname="Second", make="Honda", model="CRF450R"))
    foreign = bikes.add(_bike(other.id, nickname="Foreign"))
    store = Conversations()
    conversations = ConversationService(store, bikes)
    retrieval_calls = []

    class Retrieval:
        def search(self, user_id, bike_id, query, include_reference_editions=False):
            retrieval_calls.append(
                (user_id, bike_id, query, include_reference_editions)
            )
            return {"status": "ok", "passages": []}

    context = CompactContextService(conversations, bikes, Retrieval())
    return owner, other, bike, second, foreign, conversations, context, retrieval_calls, bikes


def test_build_includes_bike_conversation_and_deferred_stubs():
    owner, _, bike, _, _, conversations, context, _, _ = setup_context()
    thread = conversations.create(owner, bike.id)
    conversations.append_message(owner, thread.id, "valve clearance?")
    pack = context.build(owner, thread.id)
    assert pack.version == COMPACT_CONTEXT_VERSION
    assert pack.bike_id == bike.id
    assert pack.bike.nickname == "Trail"
    assert pack.bike.powertrain_type == "combustion"
    assert pack.bike.stroke_type == "4T"
    assert pack.bike.current_engine_hours == 12.5
    assert pack.conversation.rolling_summary == "user: valve clearance?"
    assert len(pack.conversation.recent_turns) == 1
    assert pack.modifications.available is False
    assert pack.maintenance.reason == "domain_not_implemented"
    assert pack.ride.available is False
    assert pack.budget.recent_turns_included == 1
    assert pack.budget.recent_turns_omitted == 0


def test_build_enforces_owner_isolation_and_records_bike_switch():
    owner, other, bike, second, _, conversations, context, _, _ = setup_context()
    thread = conversations.create(owner, bike.id)
    conversations.append_message(owner, thread.id, "hello")
    conversations.switch_bike(owner, thread.id, second.id)
    pack = context.build(owner, thread.id)
    assert pack.bike_id == second.id
    assert pack.conversation.current_bike_id == second.id
    assert pack.conversation.boundary_count == 1
    assert pack.conversation.latest_bike_switch is not None
    assert pack.conversation.latest_bike_switch.to_bike_id == second.id
    with pytest.raises(ConversationNotFound):
        context.build(other, thread.id)


def test_select_recent_turns_truncates_oldest_by_budget():
    conversation_id = uuid4()
    bike_id = uuid4()
    messages = [
        ConversationMessage(
            id=uuid4(),
            conversation_id=conversation_id,
            role="user",
            content="a" * 100,
            bike_context_id=bike_id,
            created_at=datetime.now(UTC),
        )
        for _ in range(5)
    ]
    turns, chars, omitted = select_recent_turns(messages, turn_limit=8, char_budget=250)
    assert len(turns) == 2
    assert chars == 200
    assert omitted == 3


def test_search_manuals_delegates_to_retrieval_with_ownership():
    owner, other, bike, _, foreign, _, context, calls, _ = setup_context()
    result = context.search_manuals(owner, bike.id, "torque")
    assert result["status"] == "ok"
    assert calls == [(owner.id, bike.id, "torque", False)]
    with pytest.raises(ConversationNotFound):
        context.search_manuals(owner, foreign.id, "torque")
    with pytest.raises(ConversationNotFound):
        context.search_manuals(other, bike.id, "torque")
