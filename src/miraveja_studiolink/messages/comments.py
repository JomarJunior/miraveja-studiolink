"""PersonaComment: a persona's comment or reply, publish path (FR-025 to FR-033)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from miraveja_studiolink.messages.base import ClosedModel
from miraveja_studiolink.messages.common import PersonaRef, Verdict


class PieceTarget(ClosedModel):
    pieceId: uuid.UUID


class CommentIdTarget(ClosedModel):
    commentId: uuid.UUID


CommentTarget = PieceTarget | CommentIdTarget


class PersonaComment(ClosedModel):
    sendMark: uuid.UUID
    persona: PersonaRef
    target: CommentTarget
    text: str = Field(min_length=1, max_length=4000)
    verdict: Verdict
    writtenAt: datetime


class CommentPublished(ClosedModel):
    """201 response: published, or already published under this sendMark."""

    commentId: uuid.UUID
