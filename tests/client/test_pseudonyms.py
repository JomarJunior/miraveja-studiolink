"""Per-persona pseudonyms: stable, different across personas, opaque (T037).

FR-017, FR-017a, SC-010, R-6.
"""

from __future__ import annotations

import uuid

import pytest


async def _seed_piece(state, persona_id, public_name) -> uuid.UUID:
    piece_id = uuid.uuid4()
    await state.seed_exhibited_piece(
        piece_id=piece_id,
        persona_id=persona_id,
        public_name=public_name,
        title="t",
        statement="s",
        neutral_description="d",
    )
    return piece_id


@pytest.mark.asyncio
async def test_a_visitors_pseudonym_is_stable_across_two_encounters_with_one_persona(
    client, state, persona
) -> None:
    piece_id = await _seed_piece(state, persona.personaId, persona.publicName)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="first")
    await state.script_reaction(piece_id=piece_id, visitor_id="marisol", reaction="love")

    batch = await client.collect_experiences(persona.personaId, limit=100)

    comment_pseudonym = next(i for i in batch.items if i.kind == "comment").author.pseudonym
    reaction_pseudonym = next(i for i in batch.items if i.kind == "reaction").visitor.pseudonym
    assert comment_pseudonym == reaction_pseudonym


@pytest.mark.asyncio
async def test_the_same_visitor_gets_a_different_pseudonym_for_a_different_persona(
    client, state, persona, other_persona
) -> None:
    piece_a = await _seed_piece(state, persona.personaId, persona.publicName)
    piece_b = await _seed_piece(state, other_persona.personaId, other_persona.publicName)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_a, visitor_id="marisol", text="to persona A")
    await state.script_comment(piece_id=piece_b, visitor_id="marisol", text="to persona B")

    batch_a = await client.collect_experiences(persona.personaId)
    batch_b = await client.collect_experiences(other_persona.personaId)

    pseudonym_a = batch_a.items[0].author.pseudonym
    pseudonym_b = batch_b.items[0].author.pseudonym
    assert pseudonym_a != pseudonym_b


@pytest.mark.asyncio
async def test_pseudonyms_are_opaque_and_carry_no_visitor_identifier(
    client, state, persona
) -> None:
    piece_id = await _seed_piece(state, persona.personaId, persona.publicName)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hi")

    batch = await client.collect_experiences(persona.personaId)
    pseudonym = batch.items[0].author.pseudonym

    assert "marisol" not in pseudonym
    assert 16 <= len(pseudonym) <= 128


def test_the_studio_is_given_no_secret_to_compare_pseudonyms_with(state) -> None:
    # The contract's own messages (data-model.md) carry only pseudonym + displayName; the
    # keying secret used to derive them never appears on any model the Studio can see.
    from miraveja_studiolink.messages import SCHEMA_MODELS

    visitor_ref_fields = set(SCHEMA_MODELS["VisitorRef"].model_fields)
    assert visitor_ref_fields == {"pseudonym", "displayName"}
