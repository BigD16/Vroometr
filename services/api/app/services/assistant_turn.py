"""Orchestrate a user message plus ReasoningAgent reply on a conversation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from app.assistant_tools.types import ToolContext
from app.models.conversation import ConversationMessage, MessageRole
from app.models.user import User
from app.services.conversations import ConversationDetail, ConversationService
from app.services.reasoning_agent import AgentReply, ReasoningAgent


@dataclass(frozen=True, slots=True)
class AssistantTurnResult:
    detail: ConversationDetail
    user_message: ConversationMessage
    assistant_message: ConversationMessage | None
    reply: AgentReply


class AssistantTurnService:
    """User message → optional agent reply persisted as an assistant message."""

    def __init__(
        self,
        conversations: ConversationService,
        agent: ReasoningAgent,
        tool_context_factory,
    ) -> None:
        self._conversations = conversations
        self._agent = agent
        self._tool_context_factory = tool_context_factory

    def send_user_message(
        self, user: User, conversation_id: UUID, content: str
    ) -> AssistantTurnResult:
        user_message = self._conversations.append_message(
            user, conversation_id, content, role=MessageRole.USER.value
        )
        detail = self._conversations.get(user, conversation_id)
        tool_context: ToolContext = self._tool_context_factory(
            user,
            conversation_id=conversation_id,
            bike_id=detail.conversation.current_bike_id,
        )
        reply = self._agent.run(tool_context, user_message.content)
        assistant_message = None
        if reply.status == "ok" and reply.content.strip():
            citations_json = (
                json.dumps([item.as_dict() for item in reply.citations])
                if reply.citations
                else None
            )
            assistant_message = self._conversations.append_message(
                user,
                conversation_id,
                reply.content,
                role=MessageRole.ASSISTANT.value,
                citations_json=citations_json,
            )
        detail = self._conversations.get(user, conversation_id)
        return AssistantTurnResult(
            detail=detail,
            user_message=user_message,
            assistant_message=assistant_message,
            reply=reply,
        )
