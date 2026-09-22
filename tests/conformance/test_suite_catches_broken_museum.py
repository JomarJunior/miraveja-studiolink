"""The conformance suite itself must fail a deliberately broken Museum end (T027).

Written before conformance/suite.py existed, as Principle VII requires; the three
scenarios named in the task are the ones this file exercises: a double-delivery, a
missing refusal, and a count leaking in a response.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from miraveja_studiolink.client.client import StudioLinkClient
from miraveja_studiolink.conformance.suite import (
    check_comment_without_verdict_is_refused,
    check_experiences_never_redeliver_after_acknowledgement,
    run_suite_async,
)
from miraveja_studiolink.standin.app import create_app
from tests.conformance.broken_apps import double_delivery_app, missing_refusal_app
from tests.helpers import synthetic_persona

CREDENTIAL = "test-credential"


@pytest.mark.asyncio
async def test_the_suite_catches_double_delivery() -> None:
    from miraveja_studiolink.standin.state import StandInState

    state = StandInState(CREDENTIAL)
    persona = synthetic_persona("Synthetic Double Delivery Persona")
    piece_id = uuid.uuid4()
    await state.seed_exhibited_piece(
        piece_id=piece_id,
        persona_id=persona.personaId,
        public_name=persona.publicName,
        title="t",
        statement="s",
        neutral_description="d",
    )
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hi")

    broken_app = double_delivery_app(state)
    async with StudioLinkClient(
        "http://standin", CREDENTIAL, transport=httpx.ASGITransport(app=broken_app)
    ) as client:
        with pytest.raises(AssertionError, match="delivered again"):
            await check_experiences_never_redeliver_after_acknowledgement(client, persona=persona)


@pytest.mark.asyncio
async def test_the_suite_catches_a_missing_refusal() -> None:
    from miraveja_studiolink.standin.state import StandInState

    state = StandInState(CREDENTIAL)
    broken_app = missing_refusal_app(state)
    async with StudioLinkClient(
        "http://standin", CREDENTIAL, transport=httpx.ASGITransport(app=broken_app)
    ) as client:
        with pytest.raises(AssertionError, match="was accepted"):
            await check_comment_without_verdict_is_refused(client)


@pytest.mark.asyncio
async def test_the_suite_catches_a_metric_leaking_into_a_response() -> None:
    from miraveja_studiolink.standin.state import StandInState

    state = StandInState(CREDENTIAL)
    state.force_response(
        "collectExperiences",
        {
            "items": [
                {
                    "sequence": 1,
                    "kind": "reaction",
                    "occurredAt": "2026-09-22T12:00:00Z",
                    "visitor": {
                        "pseudonym": "v-0000000000000000000a",
                        "displayName": "marisol",
                    },
                    "reaction": "love",
                    "onPieceId": str(uuid.uuid4()),
                    "reactionCount": 12,
                }
            ],
            "nextSequence": None,
        },
    )
    app = create_app(state)

    report = await run_suite_async(
        "http://standin", CREDENTIAL, transport=httpx.ASGITransport(app=app)
    )

    experiences_result = next(
        r for r in report.results if r.name.startswith("experiences are never redelivered")
    )
    assert experiences_result.status == "fail"
    assert not report.all_passed
