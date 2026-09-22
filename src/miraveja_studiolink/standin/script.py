"""Loads a YAML scripting fixture into a `StandInState` (FR-036, quickstart Scenario 2).

A minimal declarative shape: visitors, exhibited pieces, comments, reactions, gate
outcomes and closed conversations, all using synthetic personas and visitors only
(Principle VIII, SC-008). See `tests/fixtures/one-visitor-comment.yaml` for an example.
"""

from __future__ import annotations

import uuid
from typing import Any

from miraveja_studiolink.standin.state import StandInState


async def apply_script(state: StandInState, data: dict[str, Any]) -> None:
    for visitor in data.get("visitors", []):
        state.add_visitor(visitor["id"], visitor["displayName"])

    for piece in data.get("pieces", []):
        await state.seed_exhibited_piece(
            piece_id=uuid.UUID(piece["id"]),
            persona_id=uuid.UUID(piece["personaId"]),
            public_name=piece["publicName"],
            title=piece["title"],
            statement=piece["statement"],
            neutral_description=piece["neutralDescription"],
            labels=piece.get("labels", []),
        )

    for comment in data.get("comments", []):
        await state.script_comment(
            piece_id=uuid.UUID(comment["pieceId"]),
            visitor_id=comment["visitorId"],
            text=comment["text"],
        )

    for reaction in data.get("reactions", []):
        await state.script_reaction(
            piece_id=uuid.UUID(reaction["pieceId"]),
            visitor_id=reaction["visitorId"],
            reaction=reaction["reaction"],
        )

    for closure in data.get("closedConversations", []):
        state.close_conversation(uuid.UUID(closure["personaId"]), closure["visitorId"])
