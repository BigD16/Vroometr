"""Build the default read-only assistant tool registry."""

from app.assistant_tools.read_tools import (
    EXPAND_CONVERSATION_MEMORY,
    GET_BIKE,
    GET_COMPACT_CONTEXT,
    GET_CONVERSATION,
    SEARCH_CONVERSATION_MEMORY,
    SEARCH_MANUALS,
    execute_expand_conversation_memory,
    execute_get_bike,
    execute_get_compact_context,
    execute_get_conversation,
    execute_search_conversation_memory,
    execute_search_manuals,
)
from app.assistant_tools.registry import ToolRegistry


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(GET_BIKE, execute_get_bike)
    registry.register(GET_COMPACT_CONTEXT, execute_get_compact_context)
    registry.register(SEARCH_MANUALS, execute_search_manuals)
    registry.register(SEARCH_CONVERSATION_MEMORY, execute_search_conversation_memory)
    registry.register(EXPAND_CONVERSATION_MEMORY, execute_expand_conversation_memory)
    registry.register(GET_CONVERSATION, execute_get_conversation)
    return registry
