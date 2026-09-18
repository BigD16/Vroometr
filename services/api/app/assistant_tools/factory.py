"""Build the default read-only assistant tool registry."""

from app.assistant_tools.read_tools import (
    GET_BIKE,
    GET_COMPACT_CONTEXT,
    GET_CONVERSATION,
    SEARCH_MANUALS,
    execute_get_bike,
    execute_get_compact_context,
    execute_get_conversation,
    execute_search_manuals,
)
from app.assistant_tools.registry import ToolRegistry


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(GET_BIKE, execute_get_bike)
    registry.register(GET_COMPACT_CONTEXT, execute_get_compact_context)
    registry.register(SEARCH_MANUALS, execute_search_manuals)
    registry.register(GET_CONVERSATION, execute_get_conversation)
    return registry
