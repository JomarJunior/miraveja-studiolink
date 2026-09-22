"""Erasure notices: their own queue, own cursor, never presented as an experience (T035).

FR-044 to FR-047, SC-009, quickstart Scenario 7.
"""

from __future__ import annotations

import uuid

import pytest


async def _seed_piece(state, persona) -> uuid.UUID:
    piece_id = uuid.uuid4()
    await state.seed_exhibited_piece(
        piece_id=piece_id,
        persona_id=persona.personaId,
        public_name=persona.publicName,
        title="t",
        statement="s",
        neutral_description="d",
    )
    return piece_id


@pytest.mark.asyncio
async def test_an_erased_visitor_leaves_a_notice_naming_only_the_pseudonym(
    client, state, persona
) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hi")
    expected_pseudonym = state.pseudonym_for(persona.personaId, "marisol")

    await state.erase_visitor("marisol")

    batch = await client.collect_erasure_notices(persona.personaId)
    assert len(batch.items) == 1
    assert batch.items[0].pseudonym == expected_pseudonym


@pytest.mark.asyncio
async def test_erasure_notices_are_collected_independently_of_experiences(
    client, state, persona
) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hi")
    await state.erase_visitor("marisol")

    # Collecting erasure notices alone, with no experience collection at all.
    batch = await client.collect_erasure_notices(persona.personaId)
    assert len(batch.items) == 1

    # And the notice never appears among the experiences.
    experiences = await client.collect_experiences(persona.personaId, limit=100)
    assert all(item.kind != "erasure_notice" for item in experiences.items)


@pytest.mark.asyncio
async def test_erasure_notices_have_their_own_acknowledgement_cursor(
    client, state, persona
) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hi")
    await state.erase_visitor("marisol")

    batch = await client.collect_erasure_notices(persona.personaId)
    await client.acknowledge_erasure_notices(persona.personaId, batch.items[-1].sequence)

    again = await client.collect_erasure_notices(persona.personaId)
    assert again.items == []


@pytest.mark.asyncio
async def test_a_former_visitor_appears_with_no_display_name_after_erasure(
    client, state, persona
) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="before erasure")

    await state.erase_visitor("marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="after erasure")

    batch = await client.collect_experiences(persona.personaId, limit=100)
    comments = [item for item in batch.items if item.kind == "comment"]
    assert all(c.author.displayName is None for c in comments)
