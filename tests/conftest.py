from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio

from miraveja_studiolink.client.client import StudioLinkClient
from miraveja_studiolink.standin.app import create_app
from miraveja_studiolink.standin.state import StandInState
from tests.helpers import synthetic_persona

CREDENTIAL = "test-credential"


@pytest.fixture
def state() -> StandInState:
    return StandInState(CREDENTIAL)


@pytest_asyncio.fixture
async def client(state: StandInState) -> AsyncIterator[StudioLinkClient]:
    app = create_app(state)
    transport = httpx.ASGITransport(app=app)
    async with StudioLinkClient("http://standin", CREDENTIAL, transport=transport) as c:
        yield c


@pytest.fixture
def persona():
    return synthetic_persona("Synthetic Persona One")


@pytest.fixture
def other_persona():
    return synthetic_persona("Synthetic Persona Two")
