"""Shared messages: PersonaRef, VisitorRef, Verdict, Acknowledgement (data-model.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from miraveja_studiolink.messages.base import ClosedModel


class PersonaRef(ClosedModel):
    """A persona's stable identifier and public name. Never the persona definition (FR-034)."""

    personaId: uuid.UUID
    publicName: str = Field(min_length=1, max_length=80)


class VisitorRef(ClosedModel):
    """How a visitor appears to one persona: a per-persona pseudonym plus display name (FR-017)."""

    # Opaque by construction: the pattern stops a pseudonym carrying prose, and so stops
    # it becoming somewhere a metric could hide (FR-021).
    pseudonym: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    displayName: str | None = Field(min_length=1, max_length=80)


VerdictScope = Literal["charter_and_quality", "hard_lines_only"]


class Verdict(ClosedModel):
    """The AI gate's verdict. Carries no score, rating or confidence value (Principle II)."""

    outcome: Literal["accepted"]
    reason: str = Field(min_length=1, max_length=2000)
    decidedAt: datetime
    scope: VerdictScope


class Acknowledgement(ClosedModel):
    """Accept everything through a sequence number; it must never be delivered again (FR-019)."""

    throughSequence: int = Field(ge=1)
