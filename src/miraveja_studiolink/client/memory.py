"""A refusal the Studio may remember (FR-033, R-11).

The Museum side never queues a refusal as an experience: it reaches the Studio only in
the response to the Studio's own request. What the Studio does with it is its own
business; this just gives the shape of "something a persona may remember" without ever
revealing *why* a visitor stopped interacting (Charter 7.2).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from miraveja_studiolink.messages.refusal import RefusalReason, RefusalReceived


@dataclass(frozen=True)
class RememberedRefusal:
    personaId: uuid.UUID
    reason: RefusalReason
    occurredAt: datetime


def remember_refusal(
    persona_id: uuid.UUID, exc: RefusalReceived, *, occurred_at: datetime | None = None
) -> RememberedRefusal:
    return RememberedRefusal(
        personaId=persona_id, reason=exc.reason, occurredAt=occurred_at or datetime.now(UTC)
    )
