"""PresenceAnnouncement (FR-009, FR-010)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from miraveja_studiolink.messages.base import ClosedModel
from miraveja_studiolink.messages.common import PersonaRef

PresenceState = Literal["in_the_studio", "away", "resting"]


class PresenceAnnouncement(ClosedModel):
    persona: PersonaRef
    state: PresenceState
    announcedAt: datetime
