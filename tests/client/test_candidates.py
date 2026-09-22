"""Hand over a candidate; it lands with the human gate, never the exhibition (T016).

FR-012 to FR-015.
"""

from __future__ import annotations

import json
import uuid

import pytest

from miraveja_studiolink.messages.refusal import RefusalReceived
from tests.helpers import TINY_PNG, accepted_verdict


@pytest.mark.asyncio
async def test_a_well_formed_candidate_is_accepted_and_queued_for_the_human_gate(
    client, state, persona
) -> None:
    piece_id = uuid.uuid4()
    result = await client.hand_over_candidate(
        send_mark=uuid.uuid4(),
        persona=persona,
        piece_id=piece_id,
        title="Low Tide, Remembered",
        statement="I kept the horizon out of it.",
        neutral_description="A wide seascape at dusk.",
        labels=[],
        verdict=accepted_verdict(),
        image_bytes=TINY_PNG,
    )

    assert result.pieceId == piece_id
    assert result.state == "with_the_human_gate"
    assert state.pieces[piece_id].state == "with_the_human_gate"

    # Never exhibited directly (FR-014): looking at the museum shows nothing yet.
    view = await client.look_at_the_museum(persona.personaId)
    assert view.pieces == []


@pytest.mark.asyncio
async def test_resending_the_same_send_mark_yields_one_candidate_and_the_same_answer(
    client, state, persona
) -> None:
    send_mark = uuid.uuid4()
    piece_id = uuid.uuid4()
    kwargs = dict(
        send_mark=send_mark,
        persona=persona,
        piece_id=piece_id,
        title="Low Tide",
        statement="statement",
        neutral_description="description",
        labels=[],
        verdict=accepted_verdict(),
        image_bytes=TINY_PNG,
    )

    first = await client.hand_over_candidate(**kwargs)
    second = await client.hand_over_candidate(**kwargs)

    assert first == second
    assert len(state.pieces) == 1


@pytest.mark.asyncio
async def test_an_unknown_label_is_refused(client, persona) -> None:
    from miraveja_studiolink.client.transport import V1

    files = {"image": ("piece.png", TINY_PNG, "image/png")}
    candidate_json = json.dumps(
        {
            "sendMark": str(uuid.uuid4()),
            "persona": {"personaId": str(persona.personaId), "publicName": persona.publicName},
            "pieceId": str(uuid.uuid4()),
            "title": "t",
            "statement": "s",
            "neutralDescription": "d",
            "labels": ["spicy"],
            "verdict": {
                "outcome": "accepted",
                "reason": "fine",
                "decidedAt": "2026-09-22T09:00:00Z",
                "scope": "charter_and_quality",
            },
        }
    )

    with pytest.raises(RefusalReceived) as excinfo:
        await client._transport.request(
            "POST",
            f"{V1}/candidates",
            data={"candidate": candidate_json},
            files=files,
        )
    assert excinfo.value.reason == "unknown_label"


@pytest.mark.asyncio
async def test_a_candidate_without_an_accepted_verdict_is_refused(client, persona) -> None:
    from miraveja_studiolink.client.transport import V1

    files = {"image": ("piece.png", TINY_PNG, "image/png")}
    candidate_json = json.dumps(
        {
            "sendMark": str(uuid.uuid4()),
            "persona": {"personaId": str(persona.personaId), "publicName": persona.publicName},
            "pieceId": str(uuid.uuid4()),
            "title": "t",
            "statement": "s",
            "neutralDescription": "d",
            "labels": [],
        }
    )

    with pytest.raises(RefusalReceived) as excinfo:
        await client._transport.request(
            "POST", f"{V1}/candidates", data={"candidate": candidate_json}, files=files
        )
    assert excinfo.value.reason == "missing_verdict"
