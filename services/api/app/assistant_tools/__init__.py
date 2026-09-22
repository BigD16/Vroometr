"""Thin assistant tools that call the same domain services as HTTP.

Read-only tools ship in 5.3 (+ hierarchical memory tools in 5.6). Write policy (5.4)
gates any future mutating tools. Citations/safety (5.5) decide withhold vs cite vs
escalate for claims. The ReasoningAgent loop and ChatModel tool-calling are later
Phase 5 work.
"""

from app.assistant_tools.citations import (
    AnswerAction,
    Citation,
    ClaimAnswerDecision,
    ClaimRisk,
    EscalationReason,
    citations_from_retrieval_passages,
    decide_from_retrieval,
    evaluate_claim_answer,
    evaluate_escalation,
)
from app.assistant_tools.factory import build_default_registry
from app.assistant_tools.registry import ToolRegistry
from app.assistant_tools.types import ToolContext, ToolResult, ToolSpec
from app.assistant_tools.write_policy import (
    WriteClass,
    WriteDecision,
    WritePolicyResult,
    evaluate_write_policy,
)

__all__ = [
    "AnswerAction",
    "ClaimAnswerDecision",
    "ClaimRisk",
    "Citation",
    "EscalationReason",
    "ToolContext",
    "ToolRegistry",
    "ToolResult",
    "ToolSpec",
    "WriteClass",
    "WriteDecision",
    "WritePolicyResult",
    "build_default_registry",
    "citations_from_retrieval_passages",
    "decide_from_retrieval",
    "evaluate_claim_answer",
    "evaluate_escalation",
    "evaluate_write_policy",
]
