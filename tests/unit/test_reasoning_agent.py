from uuid import uuid4

from app.assistant_tools.registry import ToolRegistry
from app.assistant_tools.types import ToolContext, ToolResult, ToolSpec
from app.services.assistant_turn import AssistantTurnService
from app.services.bikes import BikeService
from app.services.hierarchical_memory import HierarchicalMemoryService
from app.services.reasoning_agent import ReasoningAgent
from tests.unit.test_compact_context import setup_context

from vroometr.ai.ports import ChatCompletionTurn, ChatToolCall
from vroometr.ai.unconfigured import UnconfiguredChatModel


class ScriptedChat:
    """Deterministic chat model for agent-loop tests."""

    def __init__(self, turns: list[ChatCompletionTurn]):
        self.turns = list(turns)
        self.calls = 0

    def complete(self, messages):
        turn = self.complete_turn(messages, tools=None)
        return turn.content or ""

    def complete_turn(self, messages, tools=None):
        if self.calls >= len(self.turns):
            raise AssertionError("unexpected extra chat call")
        turn = self.turns[self.calls]
        self.calls += 1
        return turn


def _tool_context(owner, bikes, conversations, compact_context, conversation_id, bike_id):
    return ToolContext(
        user=owner,
        bikes=BikeService(bikes),
        conversations=conversations,
        compact_context=compact_context,
        memory=HierarchicalMemoryService(conversations, bikes),
        conversation_id=conversation_id,
        bike_id=bike_id,
    )


def test_agent_invokes_tool_then_answers():
    owner, _, bike, _, _, conversations, context, calls, bikes = setup_context()
    thread = conversations.create(owner, bike.id)
    conversations.append_message(owner, thread.id, "What torque for the axle?")

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="search_manuals",
            description="search",
            parameters_schema={
                "type": "object",
                "properties": {"bike_id": {"type": "string"}, "query": {"type": "string"}},
                "required": ["bike_id", "query"],
            },
        ),
        lambda ctx, args: ToolResult.success(
            {
                "retrieval": {
                    "passages": [
                        {
                            "document_type": "manufacturer_manual",
                            "is_primary": True,
                            "section_title": "Axle",
                            "page_start": 12,
                            "page_end": 12,
                            "document_id": str(uuid4()),
                            "file_name": "manual.pdf",
                        }
                    ]
                }
            }
        ),
    )

    chat = ScriptedChat(
        [
            ChatCompletionTurn(
                content=None,
                tool_calls=(
                    ChatToolCall(
                        id="call_1",
                        name="search_manuals",
                        arguments_json=(
                            f'{{"bike_id":"{bike.id}","query":"axle torque"}}'
                        ),
                    ),
                ),
            ),
            ChatCompletionTurn(content="Axle nut torque is 105 Nm per the manual."),
        ]
    )
    agent = ReasoningAgent(chat, registry, context)
    reply = agent.run(
        _tool_context(owner, bikes, conversations, context, thread.id, bike.id),
        "What torque for the axle?",
    )
    assert reply.status == "ok"
    assert "105 Nm" in reply.content
    assert reply.tool_rounds == 1
    assert reply.citations
    assert chat.calls == 2


def test_agent_reports_awaiting_configuration():
    owner, _, bike, _, _, conversations, context, _, bikes = setup_context()
    thread = conversations.create(owner, bike.id)
    conversations.append_message(owner, thread.id, "hello")
    agent = ReasoningAgent(UnconfiguredChatModel(), ToolRegistry(), context)
    reply = agent.run(
        _tool_context(owner, bikes, conversations, context, thread.id, bike.id),
        "hello",
    )
    assert reply.status == "awaiting_configuration"


def test_assistant_turn_persists_assistant_when_ok():
    owner, _, bike, _, _, conversations, context, _, bikes = setup_context()
    thread = conversations.create(owner, bike.id)
    registry = ToolRegistry()
    chat = ScriptedChat([ChatCompletionTurn(content="Check the primary manual for torque.")])
    agent = ReasoningAgent(chat, registry, context)

    def factory(user, *, conversation_id=None, bike_id=None):
        return _tool_context(
            user, bikes, conversations, context, conversation_id, bike_id
        )

    turns = AssistantTurnService(conversations, agent, factory)
    result = turns.send_user_message(owner, thread.id, "axle torque?")
    assert result.reply.status == "ok"
    assert result.assistant_message is not None
    assert result.assistant_message.role == "assistant"
    detail = conversations.get(owner, thread.id)
    assert len(detail.messages) == 2
