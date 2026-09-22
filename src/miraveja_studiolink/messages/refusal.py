"""The closed refusal-reason list (R-10) and the exception that carries one.

No reason here expresses tone or conduct (FR-028); every reason is something the Studio
can act on mechanically (FR-032). `RefusalReceived` is raised by the client whenever the
Museum side answers with a Refusal body, or whenever the client itself decides a Museum
response cannot be trusted (an unknown field, FR-023).
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from miraveja_studiolink.messages.base import ClosedModel

RefusalReason = Literal[
    "unsupported_version",
    "not_authenticated",
    "persona_not_recognized",
    "missing_verdict",
    "rejected_verdict",
    "unknown_label",
    "unknown_field",
    "piece_not_on_display",
    "conversation_closed",
    "malformed",
]


class Refusal(ClosedModel):
    reason: RefusalReason
    detail: str | None = Field(default=None, max_length=2000)
    supportedVersions: list[str] | None = None

    @model_validator(mode="after")
    def _supported_versions_only_with_unsupported_version(self) -> Refusal:
        if self.supportedVersions is not None and self.reason != "unsupported_version":
            raise ValueError("supportedVersions is present only with unsupported_version (FR-006)")
        return self


class RefusalReceived(Exception):
    """Something in the exchange was refused, by the Museum side or by strict client checks.

    A refusal a persona may remember (FR-033); the Studio decides what, if anything, its
    persona should do with it. `detail` is for the team's logs, never for a visitor
    (Principle IV).
    """

    def __init__(
        self,
        reason: RefusalReason,
        *,
        detail: str | None = None,
        supported_versions: list[str] | None = None,
    ) -> None:
        self.reason = reason
        self.detail = detail
        self.supported_versions = supported_versions
        super().__init__(f"refused: {reason}" + (f" ({detail})" if detail else ""))

    @classmethod
    def from_refusal(cls, refusal: Refusal) -> RefusalReceived:
        return cls(
            refusal.reason,
            detail=refusal.detail,
            supported_versions=refusal.supportedVersions,
        )
