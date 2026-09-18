import pytest
from app.assistant_tools import build_default_registry
from app.assistant_tools.registry import ToolRegistry
from app.assistant_tools.types import ToolContext, ToolResult, ToolSpec
from app.services.bikes import BikeService
from tests.unit.test_compact_context import setup_context


def _tool_context(owner, bikes, conversations, compact_context, **kwargs):
    return ToolContext(
        user=owner,
        bikes=BikeService(bikes),
        conversations=conversations,
        compact_context=compact_context,
        **kwargs,
    )


def test_default_registry_is_read_only():
    registry = build_default_registry()
    names = {spec.name for spec in registry.list_specs()}
    assert names == {
        "get_bike",
        "get_compact_context",
        "search_manuals",
        "get_conversation",
    }
    assert all(not spec.mutates for spec in registry.list_specs())


def test_registry_requires_write_class_for_mutators_and_unknown_invoke():
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="write_class"):
        registry.register(
            ToolSpec(
                name="update_bike",
                description="x",
                parameters_schema={},
                mutates=True,
            ),
            lambda ctx, args: ToolResult.success({}),
        )
    owner, _, _, _, _, conversations, context, _, bikes = setup_context()
    tool_ctx = _tool_context(owner, bikes, conversations, context)
    result = registry.invoke("missing", {}, tool_ctx)
    assert result.ok is False and result.code == "unknown_tool"


def test_read_tools_enforce_ownership_and_return_payloads():
    owner, other, bike, _, foreign, conversations, context, calls, bikes = setup_context()
    registry = build_default_registry()
    tool_ctx = _tool_context(owner, bikes, conversations, context)
    thread = conversations.create(owner, bike.id)
    conversations.append_message(owner, thread.id, "oil capacity?")

    bike_result = registry.invoke("get_bike", {"bike_id": str(bike.id)}, tool_ctx)
    assert bike_result.ok is True
    assert bike_result.data["bike"]["nickname"] == "Trail"

    foreign_bike = registry.invoke("get_bike", {"bike_id": str(foreign.id)}, tool_ctx)
    assert foreign_bike.ok is False and foreign_bike.code == "not_found"

    pack = registry.invoke(
        "get_compact_context", {"conversation_id": str(thread.id)}, tool_ctx
    )
    assert pack.ok is True
    assert pack.data["context"]["bike"]["nickname"] == "Trail"

    other_ctx = _tool_context(other, bikes, conversations, context)
    denied = registry.invoke(
        "get_compact_context", {"conversation_id": str(thread.id)}, other_ctx
    )
    assert denied.ok is False and denied.code == "not_found"

    manuals = registry.invoke(
        "search_manuals",
        {"bike_id": str(bike.id), "query": "torque"},
        tool_ctx,
    )
    assert manuals.ok is True
    assert calls == [(owner.id, bike.id, "torque", False)]

    conversation = registry.invoke(
        "get_conversation", {"conversation_id": str(thread.id)}, tool_ctx
    )
    assert conversation.ok is True
    assert conversation.data["messages"][0]["content"] == "oil capacity?"
