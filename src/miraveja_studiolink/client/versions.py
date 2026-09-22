"""Ask which contract versions the Museum side supports, with no persona data (FR-007)."""

from __future__ import annotations

from miraveja_studiolink.client.strict import parse_strict
from miraveja_studiolink.client.transport import StudioLinkTransport
from miraveja_studiolink.messages.base import ClosedModel


class _VersionsResponse(ClosedModel):
    supportedVersions: list[str]


async def supported_versions(transport: StudioLinkTransport) -> list[str]:
    response = await transport.request("GET", "/studiolink/versions")
    return parse_strict(_VersionsResponse, response.json()).supportedVersions
