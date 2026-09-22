"""Collect experiences: cursor, limit, kinds, oldest first, acknowledge (T017).

FR-016 to FR-019.
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
async def test_a_scripted_comment_arrives_as_one_individual_experience(
    client, state, persona
) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hello there")

    batch = await client.collect_experiences(persona.personaId)

    assert len(batch.items) == 1
    item = batch.items[0]
    assert item.kind == "comment"
    assert item.text == "hello there"
    assert item.author.displayName == "marisol"
    assert len(item.author.pseudonym) >= 16


@pytest.mark.asyncio
async def test_reactions_and_gate_outcomes_are_their_own_kinds(client, state, persona) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_reaction(piece_id=piece_id, visitor_id="marisol", reaction="wonder")
    await state.simulate_gate_outcome(piece_id, "taken_down", reason="a rule was broken")

    batch = await client.collect_experiences(persona.personaId)

    kinds = [item.kind for item in batch.items]
    assert kinds == ["reaction", "gate_outcome"]
    assert batch.items[0].reaction == "wonder"
    assert batch.items[1].outcome == "taken_down"
    assert batch.items[1].reason == "a rule was broken"


@pytest.mark.asyncio
async def test_experiences_are_delivered_oldest_first(client, state, persona) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    for i in range(5):
        await state.script_comment(piece_id=piece_id, visitor_id="marisol", text=f"message {i}")

    batch = await client.collect_experiences(persona.personaId)

    sequences = [item.sequence for item in batch.items]
    assert sequences == sorted(sequences)
    assert [item.text for item in batch.items] == [f"message {i}" for i in range(5)]


@pytest.mark.asyncio
async def test_limit_paginates_and_next_sequence_continues(client, state, persona) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    for i in range(5):
        await state.script_comment(piece_id=piece_id, visitor_id="marisol", text=f"message {i}")

    first_page = await client.collect_experiences(persona.personaId, limit=2)
    assert len(first_page.items) == 2
    assert first_page.nextSequence == first_page.items[-1].sequence + 1

    second_page = await client.collect_experiences(
        persona.personaId, from_sequence=first_page.nextSequence, limit=2
    )
    assert len(second_page.items) == 2

    last_page = await client.collect_experiences(
        persona.personaId, from_sequence=second_page.nextSequence, limit=2
    )
    assert len(last_page.items) == 1
    assert last_page.nextSequence is None


@pytest.mark.asyncio
async def test_unacknowledged_experiences_are_delivered_again(client, state, persona) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hello")

    first = await client.collect_experiences(persona.personaId)
    second = await client.collect_experiences(persona.personaId)

    assert first.items == second.items


@pytest.mark.asyncio
async def test_acknowledged_experiences_are_never_delivered_again(client, state, persona) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hello")

    batch = await client.collect_experiences(persona.personaId)
    await client.acknowledge_experiences(persona.personaId, batch.items[-1].sequence)

    again = await client.collect_experiences(persona.personaId)
    assert again.items == []
    assert again.nextSequence is None
