"""Sameness is decided by send mark alone, never by comparing content (T032).

FR-015, FR-031, FR-031a, SC-005, quickstart Scenario 6.
"""

from __future__ import annotations

import uuid

import pytest

from tests.helpers import TINY_PNG, accepted_verdict


@pytest.mark.asyncio
async def test_resending_a_candidate_under_the_same_mark_creates_nothing_new(
    client, state, persona
) -> None:
    send_mark = uuid.uuid4()
    kwargs = dict(
        send_mark=send_mark,
        persona=persona,
        piece_id=uuid.uuid4(),
        title="t",
        statement="s",
        neutral_description="d",
        labels=[],
        verdict=accepted_verdict(),
        image_bytes=TINY_PNG,
    )

    first = await client.hand_over_candidate(**kwargs)
    for _ in range(5):
        repeat = await client.hand_over_candidate(**kwargs)
        assert repeat == first
    assert len(state.pieces) == 1


@pytest.mark.asyncio
async def test_the_same_candidate_text_under_a_new_mark_creates_a_second_one(
    client, state, persona
) -> None:
    kwargs = dict(
        persona=persona,
        title="Same Title",
        statement="Same statement, word for word.",
        neutral_description="Same description.",
        labels=[],
        verdict=accepted_verdict(),
        image_bytes=TINY_PNG,
    )

    first = await client.hand_over_candidate(
        send_mark=uuid.uuid4(), piece_id=uuid.uuid4(), **kwargs
    )
    second = await client.hand_over_candidate(
        send_mark=uuid.uuid4(), piece_id=uuid.uuid4(), **kwargs
    )

    assert first.pieceId != second.pieceId
    assert len(state.pieces) == 2


@pytest.mark.asyncio
async def test_resending_a_comment_under_the_same_mark_creates_nothing_new(
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
    send_mark = uuid.uuid4()
    kwargs = dict(
        send_mark=send_mark,
        persona=persona,
        text="the same words",
        verdict=accepted_verdict(scope="hard_lines_only"),
        target_piece_id=piece_id,
    )

    first = await client.publish_comment(**kwargs)
    for _ in range(3):
        repeat = await client.publish_comment(**kwargs)
        assert repeat == first


@pytest.mark.asyncio
async def test_a_persona_may_repeat_itself_under_a_new_mark(client, state, persona) -> None:
    """Sameness is decided by mark alone (FR-031a): identical text, new mark, new comment."""
    piece_id = uuid.uuid4()
    await state.seed_exhibited_piece(
        piece_id=piece_id,
        persona_id=persona.personaId,
        public_name=persona.publicName,
        title="t",
        statement="s",
        neutral_description="d",
    )
    kwargs = dict(
        persona=persona,
        text="I said it once and I'll say it again.",
        verdict=accepted_verdict(scope="hard_lines_only"),
        target_piece_id=piece_id,
    )

    first = await client.publish_comment(send_mark=uuid.uuid4(), **kwargs)
    second = await client.publish_comment(send_mark=uuid.uuid4(), **kwargs)

    assert first.commentId != second.commentId
