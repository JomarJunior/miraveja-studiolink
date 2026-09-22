"""Presence is ordered by the Museum side's own receipt time, not a claimed one (T036).

Edge Cases: "The Studio's clock is wrong." FR-018.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest


@pytest.mark.asyncio
async def test_a_wildly_wrong_announced_time_does_not_affect_staleness(client, state) -> None:
    persona_id = uuid.uuid4()
    persona = {"personaId": str(persona_id), "publicName": "Synthetic Persona One"}

    # The Studio's clock claims this was announced a week ago.
    bogus_time = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    await client.transport.request(
        "POST",
        "/studiolink/v1/presence",
        json={"persona": persona, "state": "in_the_studio", "announcedAt": bogus_time},
    )

    # The Museum side recorded its own receipt time just now, so the persona reads as
    # present regardless of what the claimed announcedAt said.
    assert state.presence_of(persona_id) == "in_the_studio"


@pytest.mark.asyncio
async def test_the_most_recently_received_announcement_wins_even_with_an_older_claimed_time(
    client, state
) -> None:
    persona_id = uuid.uuid4()
    persona = {"personaId": str(persona_id), "publicName": "Synthetic Persona One"}
    now = datetime.now(UTC)

    await client.transport.request(
        "POST",
        "/studiolink/v1/presence",
        json={
            "persona": persona,
            "state": "resting",
            "announcedAt": now.isoformat(),
        },
    )
    # Received second, but claims an earlier time than the first (a resend, or clock skew).
    await client.transport.request(
        "POST",
        "/studiolink/v1/presence",
        json={
            "persona": persona,
            "state": "in_the_studio",
            "announcedAt": (now - timedelta(hours=1)).isoformat(),
        },
    )

    assert state.presence_of(persona_id) == "in_the_studio"
