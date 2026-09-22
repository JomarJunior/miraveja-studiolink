"""Candidate: a piece that passed the AI gate, handed over multipart (data-model.md)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from miraveja_studiolink.messages.base import ClosedModel
from miraveja_studiolink.messages.common import PersonaRef, Verdict

Label = Literal["explicit", "violence"]


def _unique_labels(labels: list[Label]) -> list[Label]:
    if len(set(labels)) != len(labels):
        raise ValueError("labels must be unique")
    return labels


UniqueLabels = Annotated[
    list[Label],
    AfterValidator(_unique_labels),
    Field(json_schema_extra={"uniqueItems": True}),
]


class Candidate(ClosedModel):
    """The JSON part of the multipart hand-over; the image travels as the file part."""

    sendMark: uuid.UUID
    persona: PersonaRef
    pieceId: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=4000)
    neutralDescription: str = Field(min_length=1, max_length=4000)
    labels: UniqueLabels
    verdict: Verdict


class CandidateAccepted(ClosedModel):
    """202 response: accepted and queued for the human gate (FR-014)."""

    pieceId: uuid.UUID
    state: Literal["with_the_human_gate"]
