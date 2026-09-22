"""Publish a persona's comment or reply (FR-025 to FR-033)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from miraveja_studiolink.client.strict import parse_strict
from miraveja_studiolink.client.transport import V1, StudioLinkTransport
from miraveja_studiolink.messages.comments import (
    CommentIdTarget,
    CommentPublished,
    CommentTarget,
    PersonaComment,
    PieceTarget,
)
from miraveja_studiolink.messages.common import PersonaRef, Verdict


async def publish_comment(
    transport: StudioLinkTransport,
    *,
    send_mark: uuid.UUID,
    persona: PersonaRef,
    text: str,
    verdict: Verdict,
    target_piece_id: uuid.UUID | None = None,
    target_comment_id: uuid.UUID | None = None,
    written_at: datetime | None = None,
) -> CommentPublished:
    if (target_piece_id is None) == (target_comment_id is None):
        raise ValueError("exactly one of target_piece_id or target_comment_id is required")
    target: CommentTarget
    if target_piece_id is not None:
        target = PieceTarget(pieceId=target_piece_id)
    else:
        assert target_comment_id is not None
        target = CommentIdTarget(commentId=target_comment_id)
    comment = PersonaComment(
        sendMark=send_mark,
        persona=persona,
        target=target,
        text=text,
        verdict=verdict,
        writtenAt=written_at or datetime.now(UTC),
    )
    response = await transport.request(
        "POST", f"{V1}/comments", json=comment.model_dump(mode="json")
    )
    return parse_strict(CommentPublished, response.json())
