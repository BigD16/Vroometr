import pytest
from app.assistant_tools.registry import ToolRegistry
from app.assistant_tools.types import ToolContext, ToolResult, ToolSpec
from app.assistant_tools.write_policy import (
    WriteClass,
    WriteDecision,
    evaluate_write_policy,
)
from app.services.bikes import BikeService
from tests.unit.test_compact_context import setup_context


def _ctx(**kwargs):
    owner, _, _, _, _, conversations, context, _, bikes = setup_context()
    return ToolContext(
        user=owner,
        bikes=BikeService(bikes),
        conversations=conversations,
        compact_context=context,
        **kwargs,
    )


def _ok_handler(ctx, args):
    return ToolResult.success({"wrote": True})


def test_evaluate_write_policy_matrix():
    blocked = evaluate_write_policy(
        write_class=WriteClass.AUTO, writes_enabled=False
    )
    assert blocked.decision is WriteDecision.BLOCK
    assert blocked.code == "writes_disabled"

    auto = evaluate_write_policy(write_class=WriteClass.AUTO, writes_enabled=True)
    assert auto.decision is WriteDecision.ALLOW

    needs = evaluate_write_policy(write_class=WriteClass.CONFIRM, writes_enabled=True)
    assert needs.decision is WriteDecision.REQUIRE_CONFIRMATION
    assert needs.code == "confirmation_required"

    confirmed = evaluate_write_policy(
        write_class=WriteClass.CONFIRM, writes_enabled=True, confirmed=True
    )
    assert confirmed.decision is WriteDecision.ALLOW

    explicit = evaluate_write_policy(
        write_class=WriteClass.CONFIRM,
        writes_enabled=True,
        explicit_instruction=True,
    )
    assert explicit.decision is WriteDecision.ALLOW


def test_registry_gates_confirm_and_flag_for_mutating_tools():
    registry = ToolRegistry(writes_enabled=lambda: True)
    registry.register(
        ToolSpec(
            name="log_maintenance_stub",
            description="test double",
            parameters_schema={},
            mutates=True,
            write_class=WriteClass.CONFIRM,
        ),
        _ok_handler,
    )
    denied = registry.invoke("log_maintenance_stub", {}, _ctx())
    assert denied.ok is False and denied.code == "confirmation_required"

    allowed = registry.invoke(
        "log_maintenance_stub", {}, _ctx(confirmed=True)
    )
    assert allowed.ok is True and allowed.data["wrote"] is True

    explicit = registry.invoke(
        "log_maintenance_stub", {}, _ctx(explicit_instruction=True)
    )
    assert explicit.ok is True

    disabled = ToolRegistry(writes_enabled=lambda: False)
    disabled.register(
        ToolSpec(
            name="auto_tag_stub",
            description="test double",
            parameters_schema={},
            mutates=True,
            write_class=WriteClass.AUTO,
        ),
        _ok_handler,
    )
    blocked = disabled.invoke("auto_tag_stub", {}, _ctx(confirmed=True))
    assert blocked.ok is False and blocked.code == "writes_disabled"


def test_auto_write_allowed_when_flag_on():
    registry = ToolRegistry(writes_enabled=lambda: True)
    registry.register(
        ToolSpec(
            name="refresh_summary_stub",
            description="test double",
            parameters_schema={},
            mutates=True,
            write_class=WriteClass.AUTO,
        ),
        _ok_handler,
    )
    result = registry.invoke("refresh_summary_stub", {}, _ctx())
    assert result.ok is True


def test_read_tool_cannot_set_write_class():
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="write_class"):
        registry.register(
            ToolSpec(
                name="get_bike_bad",
                description="x",
                parameters_schema={},
                mutates=False,
                write_class=WriteClass.AUTO,
            ),
            _ok_handler,
        )
