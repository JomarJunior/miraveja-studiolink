"""ErasureNoticeBatch: an instruction to forget a visitor, never an experience.

FR-044 to FR-047.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from miraveja_studiolink.messages.base import ClosedModel


class ErasureNotice(ClosedModel):
    sequence: int = Field(ge=1)
    pseudonym: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    issuedAt: datetime


class ErasureNoticeBatch(ClosedModel):
    items: list[ErasureNotice] = Field(max_length=100)
    nextSequence: int | None = Field(ge=1)
