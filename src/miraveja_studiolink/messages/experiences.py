"""Experience: one individual event for one persona (FR-016 to FR-020)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from miraveja_studiolink.messages.base import ClosedModel
from miraveja_studiolink.messages.common import PersonaRef, VisitorRef

ReactionKind = Literal["love", "like", "laugh", "wonder", "sorrow"]
GateOutcome = Literal["exhibited", "declined", "taken_down"]

CommentAuthor = VisitorRef | PersonaRef


class CommentExperience(ClosedModel):
    sequence: int = Field(ge=1)
    kind: Literal["comment"]
    occurredAt: datetime
    commentId: uuid.UUID
    author: CommentAuthor
    text: str = Field(min_length=1, max_length=4000)
    onPieceId: uuid.UUID | None = None
    inReplyToCommentId: uuid.UUID | None = None


class ReactionExperience(ClosedModel):
    sequence: int = Field(ge=1)
    kind: Literal["reaction"]
    occurredAt: datetime
    visitor: VisitorRef
    reaction: ReactionKind
    onPieceId: uuid.UUID


class GateOutcomeExperience(ClosedModel):
    sequence: int = Field(ge=1)
    kind: Literal["gate_outcome"]
    occurredAt: datetime
    pieceId: uuid.UUID
    outcome: GateOutcome
    reason: str | None = Field(max_length=2000)
    """Required, but nullable: addressed to the persona where one exists."""


Experience = Annotated[
    CommentExperience | ReactionExperience | GateOutcomeExperience,
    Field(discriminator="kind"),
]


class ExperienceBatch(ClosedModel):
    items: list[Experience] = Field(max_length=100)
    nextSequence: int | None = Field(ge=1)
    """Required, but nullable: null when nothing is waiting."""
