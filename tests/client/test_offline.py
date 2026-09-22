"""The Studio keeps hours and loses nothing (T031, T034, T036b). quickstart Scenario 4.

FR-002, FR-011, FR-019, R-12, SC-004.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from miraveja_studiolink.standin.state import StandInState


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
async def test_thirty_experiences_accumulated_offline_are_all_collected_in_order(
    client, state, persona
) -> None:
    # No Studio exchange happens while these accumulate: pure state scripting.
    piece_id = await _seed_piece(state, persona)
    for i in range(30):
        visitor_id = f"visitor-{i}"
        state.add_visitor(visitor_id, visitor_id)
        await state.script_reaction(piece_id=piece_id, visitor_id=visitor_id, reaction="like")

    batch = await client.collect_experiences(persona.personaId, limit=100)

    assert len(batch.items) == 30
    sequences = [item.sequence for item in batch.items]
    assert sequences == sorted(sequences)


@pytest.mark.asyncio
async def test_an_interrupted_collection_delivers_the_same_items_again(
    client, state, persona
) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hello")

    # Simulates a collection that never reached acknowledgement (a lost connection).
    interrupted = await client.collect_experiences(persona.personaId)
    retried = await client.collect_experiences(persona.personaId)

    assert interrupted.items == retried.items


@pytest.mark.asyncio
async def test_once_acknowledged_never_delivered_again(client, state, persona) -> None:
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hello")

    batch = await client.collect_experiences(persona.personaId)
    await client.acknowledge_experiences(persona.personaId, batch.items[-1].sequence)

    again = await client.collect_experiences(persona.personaId)
    assert again.items == []


@pytest.mark.asyncio
async def test_a_persona_unheard_from_beyond_the_staleness_window_is_away() -> None:
    from datetime import UTC, datetime

    state = StandInState("test-credential", staleness_window=timedelta(minutes=1))
    persona_id = uuid.uuid4()
    state.register_persona(persona_id, "Synthetic Persona One")
    state.personas[persona_id].presence_state = "in_the_studio"
    # Simulate time passing by directly backdating the last receipt.
    state.personas[persona_id].last_seen_at = datetime.now(UTC) - timedelta(minutes=5)

    assert state.presence_of(persona_id) == "away"


@pytest.mark.asyncio
async def test_the_staleness_window_default_is_two_hours() -> None:
    from datetime import timedelta as td

    state = StandInState("test-credential")
    assert state.staleness_window == td(hours=2)


@pytest.mark.asyncio
async def test_everything_queued_holds_with_no_studio_ever_present(state, persona) -> None:
    """Every scripting call below happens with no client, no HTTP request at all."""
    piece_id = await _seed_piece(state, persona)
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="one")
    await state.script_reaction(piece_id=piece_id, visitor_id="marisol", reaction="love")
    await state.simulate_gate_outcome(piece_id, "exhibited")

    # Nothing expires: even much later, everything is still exactly as queued.
    queue = state.experience_queues[persona.personaId]
    pending, _ = await queue.collect(None, 100, 0)
    assert len(pending) == 3
