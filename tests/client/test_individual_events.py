"""Twelve reactions arrive as twelve experiences, never a summary (T024).

FR-016, User Story 2 acceptance scenario 3.
"""

from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_twelve_reactions_arrive_as_twelve_individual_experiences(
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
    visitor_ids = [f"visitor-{i}" for i in range(12)]
    for visitor_id in visitor_ids:
        state.add_visitor(visitor_id, visitor_id)
        await state.script_reaction(piece_id=piece_id, visitor_id=visitor_id, reaction="love")

    batch = await client.collect_experiences(persona.personaId, limit=100)

    assert len(batch.items) == 12
    assert all(item.kind == "reaction" for item in batch.items)
    # Each with its own visitor and time: no two share a pseudonym, none are collapsed.
    pseudonyms = {item.visitor.pseudonym for item in batch.items}
    assert len(pseudonyms) == 12
    sequences = {item.sequence for item in batch.items}
    assert len(sequences) == 12
    # And no summary anywhere: the batch itself carries no count of them beyond the
    # ordinary Python length of the list the Studio received over the wire.
    dumped = batch.model_dump()
    assert "count" not in dumped
    assert "total" not in dumped
