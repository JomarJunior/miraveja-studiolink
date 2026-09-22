"""Fetch the image of an exhibited piece — the only path an image reaches the Studio (FR-040a)."""

from __future__ import annotations

import uuid

from miraveja_studiolink.client.transport import V1, StudioLinkTransport


async def fetch_piece_image(
    transport: StudioLinkTransport, piece_id: uuid.UUID
) -> tuple[bytes, str]:
    response = await transport.request("GET", f"{V1}/pieces/{piece_id}/image")
    return response.content, response.headers.get("content-type", "application/octet-stream")
