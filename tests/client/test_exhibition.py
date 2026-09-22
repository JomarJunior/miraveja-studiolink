"""Look at the museum: named looking persona, time order, no counts (T019).

FR-040, FR-041, FR-043.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from miraveja_studiolink.messages.refusal import RefusalReceived


@pytest.mark.asyncio
async def test_looking_returns_the_scripted_exhibition_in_time_order(
    client, state, persona
) -> None:
    older = uuid.uuid4()
    newer = uuid.uuid4()
    base = datetime.now(UTC)
    await state.seed_exhibited_piece(
        piece_id=older,
        persona_id=persona.personaId,
        public_name=persona.publicName,
        title="Older Piece",
        statement="s",
        neutral_description="d",
        exhibited_at=base,
    )
    await state.seed_exhibited_piece(
        piece_id=newer,
        persona_id=persona.personaId,
        public_name=persona.publicName,
        title="Newer Piece",
        statement="s",
        neutral_description="d",
        exhibited_at=base + timedelta(minutes=1),
    )

    view = await client.look_at_the_museum(persona.personaId)

    assert [p.pieceId for p in view.pieces] == [newer, older]


@pytest.mark.asyncio
async def test_looking_changes_nothing_and_is_no_ones_experience(client, state, persona) -> None:
    piece_id = uuid.uuid4()
    await state.seed_exhibited_piece(
        piece_id=piece_id,
        persona_id=persona.personaId,
        public_name=persona.publicName,
        title="t",
        statement="s",
        neutral_description="d",
    )

    await client.look_at_the_museum(persona.personaId)
    await client.look_at_the_museum(persona.personaId)

    batch = await client.collect_experiences(persona.personaId)
    assert batch.items == []
    assert state.pieces[piece_id].state == "exhibited"


@pytest.mark.asyncio
async def test_visitor_references_use_the_looking_personas_pseudonym(
    client, state, persona, other_persona
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
    state.add_visitor("marisol", "marisol")
    await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hi")

    # A different persona is registered by announcing presence, then looks at the same piece.
    from datetime import UTC, datetime

    state.announce_presence(
        other_persona.personaId, other_persona.publicName, "in_the_studio", datetime.now(UTC)
    )

    view_as_owner = await client.look_at_the_museum(persona.personaId)
    view_as_other = await client.look_at_the_museum(other_persona.personaId)

    pseudonym_as_owner = view_as_owner.pieces[0].conversation[0].author.pseudonym
    pseudonym_as_other = view_as_other.pieces[0].conversation[0].author.pseudonym
    assert pseudonym_as_owner != pseudonym_as_other


@pytest.mark.asyncio
async def test_looking_as_an_unknown_persona_is_refused(client) -> None:
    with pytest.raises(RefusalReceived) as excinfo:
        await client.look_at_the_museum(uuid.uuid4())
    assert excinfo.value.reason == "persona_not_recognized"
