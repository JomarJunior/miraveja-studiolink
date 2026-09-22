"""Publish a persona's comment or reply (T018). FR-025 to FR-027, FR-030, FR-032."""

from __future__ import annotations

import uuid

import pytest

from miraveja_studiolink.messages.refusal import RefusalReceived
from tests.helpers import accepted_verdict


@pytest.mark.asyncio
async def test_a_reply_is_recorded_in_the_same_conversation(client, state, persona) -> None:
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
    original_comment_id = await state.script_comment(
        piece_id=piece_id, visitor_id="marisol", text="hello there"
    )
    # The Studio collects, sees the comment, and replies to it.
    await client.collect_experiences(persona.personaId)

    published = await client.publish_comment(
        send_mark=uuid.uuid4(),
        persona=persona,
        text="thank you for looking",
        verdict=accepted_verdict(scope="hard_lines_only"),
        target_comment_id=original_comment_id,
    )

    view = await client.look_at_the_museum(persona.personaId)
    conversation_ids = [c.commentId for c in view.pieces[0].conversation]
    assert original_comment_id in conversation_ids
    assert published.commentId in conversation_ids


@pytest.mark.asyncio
async def test_a_comment_without_an_accepted_verdict_is_refused(client, persona) -> None:
    from miraveja_studiolink.client.transport import V1

    with pytest.raises(RefusalReceived) as excinfo:
        await client._transport.request(
            "POST",
            f"{V1}/comments",
            json={
                "sendMark": str(uuid.uuid4()),
                "persona": {
                    "personaId": str(persona.personaId),
                    "publicName": persona.publicName,
                },
                "target": {"pieceId": str(uuid.uuid4())},
                "text": "ungated words",
                "writtenAt": "2026-09-22T18:40:09Z",
            },
        )
    assert excinfo.value.reason == "missing_verdict"


@pytest.mark.asyncio
async def test_a_tone_judgment_field_is_refused_as_unknown_field(client, persona) -> None:
    from miraveja_studiolink.client.transport import V1

    with pytest.raises(RefusalReceived) as excinfo:
        await client._transport.request(
            "POST",
            f"{V1}/comments",
            json={
                "sendMark": str(uuid.uuid4()),
                "persona": {
                    "personaId": str(persona.personaId),
                    "publicName": persona.publicName,
                },
                "target": {"pieceId": str(uuid.uuid4())},
                "text": "blunt words, freely chosen",
                "verdict": {
                    "outcome": "accepted",
                    "reason": "no hard line touched",
                    "decidedAt": "2026-09-22T18:40:11Z",
                    "scope": "hard_lines_only",
                },
                "toneAssessment": "hostile",
                "writtenAt": "2026-09-22T18:40:09Z",
            },
        )
    assert excinfo.value.reason == "unknown_field"


@pytest.mark.asyncio
async def test_commenting_on_a_piece_not_on_display_is_refused(client, persona) -> None:
    with pytest.raises(RefusalReceived) as excinfo:
        await client.publish_comment(
            send_mark=uuid.uuid4(),
            persona=persona,
            text="hello",
            verdict=accepted_verdict(scope="hard_lines_only"),
            target_piece_id=uuid.uuid4(),
        )
    assert excinfo.value.reason == "piece_not_on_display"


@pytest.mark.asyncio
async def test_replying_after_the_conversation_is_closed_is_refused(client, state, persona) -> None:
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
    assert excinfo.value.reason == "conversation_closed"
    # The refusal never says why (FR-033, Charter 7.2): only the neutral reason crosses.
    assert excinfo.value.detail is None
