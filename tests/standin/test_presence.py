"""The stand-in itself, at the wire level, accepts and reports presence (T013).

Independent of the client SDK: raw HTTP against the ASGI app, the way a non-Python
Studio implementation would see it.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from miraveja_studiolink.standin.app import create_app
from miraveja_studiolink.standin.state import StandInState


@pytest.fixture
def raw_client(state: StandInState) -> httpx.AsyncClient:
    app = create_app(state)
    return httpx.AsyncClient(
        base_url="http://standin",
        transport=httpx.ASGITransport(app=app),
        headers={"Authorization": f"Bearer {state.credential}"},
    )


@pytest.mark.asyncio
async def test_presence_announcement_returns_204(raw_client: httpx.AsyncClient, state) -> None:
    persona_id = uuid.uuid4()
    response = await raw_client.post(
        "/studiolink/v1/presence",
        json={
            "persona": {"personaId": str(persona_id), "publicName": "Synthetic Persona One"},
            "state": "in_the_studio",
            "announcedAt": "2026-09-22T09:00:00Z",
        },
    )
    assert response.status_code == 204
    assert state.presence_of(persona_id) == "in_the_studio"


@pytest.mark.asyncio
async def test_presence_without_auth_is_refused(raw_client: httpx.AsyncClient) -> None:
    raw_client.headers.pop("Authorization")
    response = await raw_client.post(
        "/studiolink/v1/presence",
        json={
            "persona": {"personaId": str(uuid.uuid4()), "publicName": "Synthetic Persona One"},
            "state": "away",
            "announcedAt": "2026-09-22T09:00:00Z",
        },
    )
    assert response.status_code == 401
    assert response.json()["reason"] == "not_authenticated"


@pytest.mark.asyncio
async def test_extra_field_is_refused_as_unknown_field(raw_client: httpx.AsyncClient) -> None:
    response = await raw_client.post(
        "/studiolink/v1/presence",
        json={
            "persona": {"personaId": str(uuid.uuid4()), "publicName": "Synthetic Persona One"},
            "state": "away",
            "announcedAt": "2026-09-22T09:00:00Z",
            "moodEmoji": "🙂",
        },
    )
    assert response.status_code == 400
    assert response.json()["reason"] == "unknown_field"
