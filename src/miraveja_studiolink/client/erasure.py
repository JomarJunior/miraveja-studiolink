"""Collect and acknowledge erasure notices, on their own cursor (FR-044 to FR-047)."""

from __future__ import annotations

import uuid

from miraveja_studiolink.client.strict import parse_strict
from miraveja_studiolink.client.transport import V1, StudioLinkTransport
from miraveja_studiolink.messages.common import Acknowledgement
from miraveja_studiolink.messages.erasure import ErasureNoticeBatch


async def collect_erasure_notices(
    transport: StudioLinkTransport,
    persona_id: uuid.UUID,
    *,
    from_sequence: int | None = None,
    limit: int = 50,
) -> ErasureNoticeBatch:
    params: dict[str, object] = {"limit": limit}
    if from_sequence is not None:
        params["fromSequence"] = from_sequence
    response = await transport.request(
        "GET", f"{V1}/personas/{persona_id}/erasure-notices", params=params
    )
    return parse_strict(ErasureNoticeBatch, response.json())


async def acknowledge_erasure_notices(
    transport: StudioLinkTransport, persona_id: uuid.UUID, through_sequence: int
) -> None:
    ack = Acknowledgement(throughSequence=through_sequence)
    await transport.request(
        "POST",
        f"{V1}/personas/{persona_id}/erasure-notices/acknowledge",
        json=ack.model_dump(mode="json"),
    )
