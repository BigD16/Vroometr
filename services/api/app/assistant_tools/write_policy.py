"""Risk-based AI write policy for assistant tools (DESIGN §6).

Classification is declarative on ToolSpec.write_class. Utterance NLP is not
done here — the caller sets confirmed / explicit_instruction on ToolContext.
"""

from dataclasses import dataclass
from enum import StrEnum


class WriteClass(StrEnum):
    AUTO = "auto"
    CONFIRM = "confirm"


class WriteDecision(StrEnum):
    ALLOW = "allow"
    REQUIRE_CONFIRMATION = "require_confirmation"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class WritePolicyResult:
    decision: WriteDecision
    code: str | None
    reason: str


def evaluate_write_policy(
    *,
    write_class: WriteClass,
    writes_enabled: bool,
    confirmed: bool = False,
    explicit_instruction: bool = False,
) -> WritePolicyResult:
    if not writes_enabled:
        return WritePolicyResult(
            decision=WriteDecision.BLOCK,
            code="writes_disabled",
            reason="AI write actions are disabled by the ai_writes flag.",
        )
    if write_class is WriteClass.AUTO:
        return WritePolicyResult(
            decision=WriteDecision.ALLOW,
            code=None,
            reason="Automatic low-risk write is allowed.",
        )
    if write_class is WriteClass.CONFIRM:
        if confirmed or explicit_instruction:
            return WritePolicyResult(
                decision=WriteDecision.ALLOW,
                code=None,
                reason="Durable write allowed after confirmation or explicit instruction.",
            )
        return WritePolicyResult(
            decision=WriteDecision.REQUIRE_CONFIRMATION,
            code="confirmation_required",
            reason=(
                "Durable machine writes require explicit instruction or user confirmation. "
                "Casual mentions are not enough."
            ),
        )
    raise ValueError(f"unknown write_class: {write_class}")
