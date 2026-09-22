"""Version negotiation (T038, T039). FR-005 to FR-007, SC-006, quickstart Scenario 6."""

from __future__ import annotations

import uuid

import pytest

from miraveja_studiolink.messages.refusal import RefusalReceived


@pytest.mark.asyncio
async def test_the_studio_can_ask_which_versions_are_supported(client) -> None:
    versions = await client.supported_versions()
    assert versions == ["1.0.0"]


@pytest.mark.asyncio
async def test_asking_which_versions_are_supported_sends_no_persona_data(client) -> None:
    # The request itself carries nothing persona-shaped: no body, no persona-scoped
    # path, no query parameters at all.
    response = await client.transport.request("GET", "/studiolink/versions")
    assert response.request.content in (b"", None)
    assert len(response.request.url.params) == 0


@pytest.mark.asyncio
async def test_an_unsupported_version_is_refused_before_any_content_is_acted_on(
    client, state
) -> None:
    persona_id = uuid.uuid4()
    with pytest.raises(RefusalReceived) as excinfo:
        await client.transport.request(
            "GET",
            "/studiolink/v99/exhibition",
            params={"asPersonaId": str(persona_id)},
        )
    assert excinfo.value.reason == "unsupported_version"
    assert excinfo.value.supported_versions == ["1.0.0"]
    # Nothing was acted on: the unknown persona was never even registered.
    assert not state.is_known_persona(persona_id)


@pytest.mark.asyncio
async def test_an_unsupported_version_is_refused_on_a_mutating_exchange_too(client) -> None:
    with pytest.raises(RefusalReceived) as excinfo:
        await client.transport.request(
            "POST",
            "/studiolink/v2/presence",
            json={
                "persona": {"personaId": str(uuid.uuid4()), "publicName": "Synthetic Persona One"},
                "state": "in_the_studio",
                "announcedAt": "2026-09-22T09:00:00Z",
            },
        )
    assert excinfo.value.reason == "unsupported_version"
    assert excinfo.value.supported_versions
