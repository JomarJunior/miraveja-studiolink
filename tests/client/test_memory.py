"""A refusal is handed to the caller as something a persona may remember (T020).

FR-033, R-11.
"""

from __future__ import annotations

import uuid

import pytest

from miraveja_studiolink.client.memory import remember_refusal
from miraveja_studiolink.messages.refusal import RefusalReceived
from tests.helpers import accepted_verdict


@pytest.mark.asyncio
async def test_a_refusal_can_be_turned_into_a_remembered_refusal(client, state, persona) -> None:
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
    comment_id = await state.script_comment(piece_id=piece_id, visitor_id="marisol", text="hi")
    state.close_conversation(persona.personaId, "marisol")

    with pytest.raises(RefusalReceived) as excinfo:
        await client.publish_comment(
            send_mark=uuid.uuid4(),
            persona=persona,
            text="a reply",
            verdict=accepted_verdict(scope="hard_lines_only"),
            target_comment_id=comment_id,
        )

    remembered = remember_refusal(persona.personaId, excinfo.value)

    assert remembered.personaId == persona.personaId
    assert remembered.reason == "conversation_closed"
    # It never reveals a visitor's choice (Charter 7.2): nothing about "marisol" survives.
    assert "marisol" not in repr(remembered)
