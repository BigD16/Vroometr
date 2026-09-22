from uuid import uuid4

import pytest
from app.models.conversation import ConversationMessage
from app.services.conversations import ConversationNotFound, InvalidConversation
from app.services.hierarchical_memory import (
    MEMORY_VERSION,
    HierarchicalMemoryService,
    expand_matching_span,
    score_overlap,
)
from tests.unit.test_compact_context import setup_context


def _memory():
    owner, other, bike, second, foreign, conversations, _, _, bikes = setup_context()
    return (
        owner,
        other,
        bike,
        second,
        foreign,
        conversations,
        HierarchicalMemoryService(conversations, bikes),
    )


def test_score_overlap_is_query_token_coverage():
    assert score_overlap("valve clearance", "user: valve clearance on the YZ") == 1.0
    assert score_overlap("valve clearance", "oil change interval") == 0.0
    assert score_overlap("", "anything") == 0.0


def test_search_summaries_ranks_bike_threads_and_excludes_current():
    owner, other, bike, second, foreign, conversations, memory = _memory()
    current = conversations.create(owner, bike.id)
    conversations.append_message(owner, current.id, "current valve question")
    older = conversations.create(owner, bike.id)
    conversations.append_message(owner, older.id, "previous valve clearance discussion")
    other_bike = conversations.create(owner, second.id)
    conversations.append_message(owner, other_bike.id, "valve clearance on second bike")
    foreign_thread = conversations.create(other, foreign.id)
    conversations.append_message(other, foreign_thread.id, "valve clearance foreign")

    result = memory.search_summaries(
        owner,
        bike.id,
        "valve clearance",
        exclude_conversation_id=current.id,
    )
    assert result["version"] == MEMORY_VERSION
    assert result["ranking"] == "token_overlap_v1"
    hit_ids = [hit["conversation_id"] for hit in result["hits"]]
    assert str(older.id) in hit_ids
    assert str(current.id) not in hit_ids
    assert str(other_bike.id) not in hit_ids
    assert str(foreign_thread.id) not in hit_ids
    assert result["hits"][0]["score"] > 0


def test_search_summaries_enforces_ownership_and_query():
    owner, other, bike, _, foreign, conversations, memory = _memory()
    thread = conversations.create(owner, bike.id)
    conversations.append_message(owner, thread.id, "oil capacity")
    with pytest.raises(ConversationNotFound):
        memory.search_summaries(owner, foreign.id, "oil")
    with pytest.raises(ConversationNotFound):
        memory.search_summaries(other, bike.id, "oil")
    with pytest.raises(InvalidConversation):
        memory.search_summaries(owner, bike.id, "   ")


def test_expand_span_returns_window_around_best_match():
    owner, _, bike, _, _, conversations, memory = _memory()
    thread = conversations.create(owner, bike.id)
    conversations.append_message(owner, thread.id, "hello")
    conversations.append_message(owner, thread.id, "talking about oil filter")
    conversations.append_message(owner, thread.id, "valve clearance specs?")
    conversations.append_message(owner, thread.id, "thanks")
    payload = memory.expand_span(owner, thread.id, "valve clearance")
    contents = [item["content"] for item in payload["span"]["messages"]]
    assert any("valve clearance" in content for content in contents)
    assert payload["span"]["chars_used"] > 0
    assert payload["rolling_summary"] is not None


def test_expand_span_owner_isolation_and_around_message():
    owner, other, bike, _, _, conversations, memory = _memory()
    thread = conversations.create(owner, bike.id)
    first = conversations.append_message(owner, thread.id, "oil change")
    conversations.append_message(owner, thread.id, "valve note")
    with pytest.raises(ConversationNotFound):
        memory.expand_span(other, thread.id, "oil")
    payload = memory.expand_span(
        owner, thread.id, "ignored-query-tokens-xyz", around_message_id=first.id
    )
    assert payload["span"]["messages"][0]["id"] == str(first.id)
    with pytest.raises(InvalidConversation):
        memory.expand_span(owner, thread.id, "oil", around_message_id=uuid4())


def test_expand_matching_span_respects_char_budget():
    conversation_id = uuid4()
    bike_id = uuid4()
    messages = [
        ConversationMessage(
            id=uuid4(),
            conversation_id=conversation_id,
            role="user",
            content="alpha valve",
            bike_context_id=bike_id,
        ),
        ConversationMessage(
            id=uuid4(),
            conversation_id=conversation_id,
            role="assistant",
            content="beta " + ("x" * 500),
            bike_context_id=bike_id,
        ),
        ConversationMessage(
            id=uuid4(),
            conversation_id=conversation_id,
            role="user",
            content="gamma valve clearance",
            bike_context_id=bike_id,
        ),
    ]
    selected, omitted_before, omitted_after, chars = expand_matching_span(
        messages,
        "valve clearance",
        message_limit=3,
        char_budget=40,
        pad=1,
    )
    assert selected
    assert chars <= 40
    assert omitted_before + len(selected) + omitted_after == len(messages)
