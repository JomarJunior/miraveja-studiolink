"""Look at what is exhibited (FR-040 to FR-043)."""

from __future__ import annotations

import uuid
from datetime import datetime

from miraveja_studiolink.client.strict import parse_strict
from miraveja_studiolink.client.transport import V1, StudioLinkTransport
from miraveja_studiolink.messages.exhibition import ExhibitionView


async def look_at_the_museum(
    transport: StudioLinkTransport,
    as_persona_id: uuid.UUID,
    *,
    before: datetime | None = None,
    limit: int = 20,
) -> ExhibitionView:
    params: dict[str, object] = {"asPersonaId": str(as_persona_id), "limit": limit}
    if before is not None:
        params["before"] = before.isoformat()
    response = await transport.request("GET", f"{V1}/exhibition", params=params)
    return parse_strict(ExhibitionView, response.json())
