"""A persona announces presence and the Museum side reports it back (FR-009, FR-010, T013)."""

from __future__ import annotations

import pytest

from miraveja_studiolink.messages.refusal import RefusalReceived


@pytest.mark.asyncio
async def test_announcing_presence_is_recorded(client, state, persona) -> None:
    await client.announce_presence(persona, "in_the_studio")

    assert state.presence_of(persona.personaId) == "in_the_studio"


@pytest.mark.asyncio
async def test_presence_states_are_reported_back(client, state, persona) -> None:
    for presence_state in ("in_the_studio", "away", "resting"):
        await client.announce_presence(persona, presence_state)
        assert state.presence_of(persona.personaId) == presence_state


@pytest.mark.asyncio
async def test_latest_announcement_wins(client, state, persona) -> None:
    await client.announce_presence(persona, "in_the_studio")
    await client.announce_presence(persona, "resting")

    assert state.presence_of(persona.personaId) == "resting"


@pytest.mark.asyncio
async def test_wrong_credential_is_refused(state, persona) -> None:
    import httpx

    from miraveja_studiolink.client.client import StudioLinkClient
    from miraveja_studiolink.standin.app import create_app

    app = create_app(state)
    async with StudioLinkClient(
        "http://standin", "wrong-token", transport=httpx.ASGITransport(app=app)
    ) as bad_client:
        with pytest.raises(RefusalReceived) as excinfo:
            await bad_client.announce_presence(persona, "in_the_studio")
        assert excinfo.value.reason == "not_authenticated"


@pytest.mark.asyncio
async def test_unknown_presence_state_is_refused(client, persona) -> None:
    # Bypass the closed Pydantic model to exercise the wire-level malformed case
    # (the fixture invalid/presence-unknown-state.json), the way a non-Python
    # Studio implementation might send it.
    from miraveja_studiolink.client.transport import V1

    with pytest.raises(RefusalReceived) as excinfo:
        await client._transport.request(
            "POST",
            f"{V1}/presence",
            json={
                "persona": {"personaId": str(persona.personaId), "publicName": persona.publicName},
                "state": "busy",
                "announcedAt": "2026-09-22T09:00:00Z",
            },
        )
    assert excinfo.value.reason == "malformed"
