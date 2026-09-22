"""ExhibitionView: looking at the museum, time-ordered, with no counts (FR-040 to FR-043)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from miraveja_studiolink.messages.base import ClosedModel
from miraveja_studiolink.messages.candidates import UniqueLabels
from miraveja_studiolink.messages.common import PersonaRef, VisitorRef

ConversationAuthor = VisitorRef | PersonaRef

ImageMediaType = Literal["image/png", "image/jpeg", "image/webp"]


class ConversationEntry(ClosedModel):
    commentId: uuid.UUID
    author: ConversationAuthor
    text: str = Field(min_length=1, max_length=4000)
    writtenAt: datetime


class ExhibitedPiece(ClosedModel):
    pieceId: uuid.UUID
    persona: PersonaRef
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=4000)
    neutralDescription: str = Field(min_length=1, max_length=4000)
    labels: UniqueLabels
    imageMediaType: ImageMediaType
    exhibitedAt: datetime
    conversation: list[ConversationEntry] = Field(max_length=200)


class ExhibitionView(ClosedModel):
    pieces: list[ExhibitedPiece] = Field(max_length=50)
    nextBefore: datetime | None
