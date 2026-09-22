"""Announce a persona's presence (FR-009, FR-010)."""

from __future__ import annotations

from datetime import UTC, datetime

from miraveja_studiolink.client.transport import V1, StudioLinkTransport
from miraveja_studiolink.messages.common import PersonaRef
from miraveja_studiolink.messages.presence import PresenceAnnouncement, PresenceState


async def announce_presence(
    transport: StudioLinkTransport,
    persona: PersonaRef,
    state: PresenceState,
    *,
    announced_at: datetime | None = None,
) -> None:
    announcement = PresenceAnnouncement(
        persona=persona, state=state, announcedAt=announced_at or datetime.now(UTC)
    )
    await transport.request("POST", f"{V1}/presence", json=announcement.model_dump(mode="json"))
