"""Collect and acknowledge experiences (FR-016 to FR-020)."""

from __future__ import annotations

import uuid

from miraveja_studiolink.client.strict import parse_strict
from miraveja_studiolink.client.transport import V1, StudioLinkTransport
from miraveja_studiolink.messages.common import Acknowledgement
from miraveja_studiolink.messages.experiences import ExperienceBatch


async def collect_experiences(
    transport: StudioLinkTransport,
    persona_id: uuid.UUID,
    *,
    from_sequence: int | None = None,
    limit: int = 50,
    wait_seconds: int = 0,
) -> ExperienceBatch:
    params: dict[str, object] = {"limit": limit, "waitSeconds": wait_seconds}
    if from_sequence is not None:
        params["fromSequence"] = from_sequence
    response = await transport.request(
        "GET", f"{V1}/personas/{persona_id}/experiences", params=params
    )
    return parse_strict(ExperienceBatch, response.json())


async def acknowledge_experiences(
    transport: StudioLinkTransport, persona_id: uuid.UUID, through_sequence: int
) -> None:
    ack = Acknowledgement(throughSequence=through_sequence)
    await transport.request(
        "POST",
        f"{V1}/personas/{persona_id}/experiences/acknowledge",
        json=ack.model_dump(mode="json"),
    )
