"""The stand-in never emits a metric field at runtime, however busy it is (T026).

Checks behavior rather than the document, so a future end could pass the static review
(test_no_metric_fields.py) and still leak at runtime — this is what would catch it.
"""

from __future__ import annotations

import uuid

import pytest

from tests.helpers import TINY_PNG, accepted_verdict
from tests.metrics_check import collect_object_keys, offending_field_names


@pytest.mark.asyncio
async def test_a_busy_persona_emits_no_metric_field_anywhere(client, state, persona) -> None:
    piece_id = uuid.uuid4()
    await state.seed_exhibited_piece(
        piece_id=piece_id,
        persona_id=persona.personaId,
        public_name=persona.publicName,
        title="t",
        statement="s",
        neutral_description="d",
        image_bytes=TINY_PNG,
    )
    for i in range(25):
        visitor_id = f"visitor-{i}"
        state.add_visitor(visitor_id, visitor_id)
        await state.script_reaction(piece_id=piece_id, visitor_id=visitor_id, reaction="love")
        await state.script_comment(piece_id=piece_id, visitor_id=visitor_id, text=f"note {i}")
    await state.simulate_gate_outcome(piece_id, "exhibited")

    second_piece = uuid.uuid4()
    await client.hand_over_candidate(
        send_mark=uuid.uuid4(),
        persona=persona,
        piece_id=second_piece,
        title="Second",
        statement="s",
        neutral_description="d",
        labels=[],
        verdict=accepted_verdict(),
        image_bytes=TINY_PNG,
    )

    responses: list[object] = []
    responses.append((await client.collect_experiences(persona.personaId, limit=100)).model_dump())
    responses.append((await client.look_at_the_museum(persona.personaId)).model_dump())
    responses.append({"supportedVersions": await client.supported_versions()})

    keys = collect_object_keys(responses)
    offenders = offending_field_names(keys)
    assert not offenders, f"runtime response carried metric-looking field(s): {offenders}"


@pytest.mark.asyncio
async def test_twelve_reactions_produce_no_count_however_they_are_collected(
    client, state, persona
) -> None:
    piece_id = uuid.uuid4()
    await state.seed_exhibited_piece(
        piece_id=piece_id,
        persona_id=persona.personaId,
        public_name=persona.publicName,
        title="t",
        statement="s",
        neutral_description="d",
    )
    for i in range(12):
        visitor_id = f"reactor-{i}"
        state.add_visitor(visitor_id, visitor_id)
        await state.script_reaction(piece_id=piece_id, visitor_id=visitor_id, reaction="wonder")

    # Ask for it in small pages: pagination itself must not leak a running total.
    all_items = []
    cursor = None
    while True:
        batch = await client.collect_experiences(persona.personaId, from_sequence=cursor, limit=3)
        all_items.extend(batch.model_dump()["items"])
        if batch.nextSequence is None:
            break
        cursor = batch.nextSequence

    assert len(all_items) == 12
    offenders = offending_field_names(collect_object_keys(all_items))
    assert not offenders
