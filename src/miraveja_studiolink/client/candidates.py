"""Hand over a candidate that passed the AI gate (FR-012 to FR-015)."""

from __future__ import annotations

import uuid

from miraveja_studiolink.client.strict import parse_strict
from miraveja_studiolink.client.transport import V1, StudioLinkTransport
from miraveja_studiolink.messages.candidates import Candidate, CandidateAccepted, Label
from miraveja_studiolink.messages.common import PersonaRef, Verdict


async def hand_over_candidate(
    transport: StudioLinkTransport,
    *,
    send_mark: uuid.UUID,
    persona: PersonaRef,
    piece_id: uuid.UUID,
    title: str,
    statement: str,
    neutral_description: str,
    labels: list[Label],
    verdict: Verdict,
    image_bytes: bytes,
    image_media_type: str = "image/png",
) -> CandidateAccepted:
    candidate = Candidate(
        sendMark=send_mark,
        persona=persona,
        pieceId=piece_id,
        title=title,
        statement=statement,
        neutralDescription=neutral_description,
        labels=labels,
        verdict=verdict,
    )
    response = await transport.request(
        "POST",
        f"{V1}/candidates",
        data={"candidate": candidate.model_dump_json()},
        files={"image": ("piece.img", image_bytes, image_media_type)},
    )
    return parse_strict(CandidateAccepted, response.json())
