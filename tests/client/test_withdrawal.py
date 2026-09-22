"""An experience whose comment or reaction is removed before collection is withdrawn (T033).

FR-020.
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
async def test_a_comment_withdrawn_before_collection_is_never_delivered(
    client, state, persona
) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    comment_id = await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hi")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="still here")

    state.withdraw_comment(comment_id)

    batch = await client.collect_experiences(persona.personaId, limit=100)
    delivered_comment_ids = [item.commentId for item in batch.items if item.kind == "comment"]
    assert comment_id not in delivered_comment_ids
    assert len(batch.items) == 1


@pytest.mark.asyncio
async def test_a_reaction_withdrawn_before_collection_is_never_delivered(
    client, state, persona
) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    state.add_visitor("quiet-tide", "quiet_tide")
    reaction_id = await state.script_reaction(
        piece_id=piece_id, visitor_id="marisol", reaction="sorrow"
    )
    await state.script_reaction(piece_id=piece_id, visitor_id="quiet-tide", reaction="wonder")

    state.withdraw_reaction(piece_id, reaction_id)

    batch = await client.collect_experiences(persona.personaId, limit=100)
    assert len(batch.items) == 1
    assert batch.items[0].reaction == "wonder"


@pytest.mark.asyncio
async def test_withdrawal_leaves_no_trace_of_the_withdrawal_mechanism_on_the_wire(
    client, state, persona
) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_reaction(piece_id=piece_id, visitor_id="marisol", reaction="like")

    batch = await client.collect_experiences(persona.personaId)
    dumped = batch.model_dump()
    assert not any(key.startswith("__") for item in dumped["items"] for key in item)
