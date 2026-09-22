"""The one place every Studio Link request is made (FR-004, R-3, R-9).

Every exchange is an HTTPS request started by the Studio, carrying one bearer credential
that identifies the Studio, never a persona (R-9). `StudioLinkTransport` is the single
chokepoint: it attaches the credential, and turns any non-2xx response into a
`RefusalReceived` the caller can act on (R-10), so no client submodule reimplements
error handling.
"""

from __future__ import annotations

from typing import Any

import httpx

from miraveja_studiolink.client.strict import parse_strict
from miraveja_studiolink.messages.refusal import Refusal, RefusalReceived

V1 = "/studiolink/v1"


class StudioLinkTransport:
    def __init__(
        self,
        base_url: str,
        credential: str,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 35.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {credential}"},
            transport=transport,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> StudioLinkTransport:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Make one request. Raises `RefusalReceived` for any non-2xx response."""
        response = self._client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise self._refusal_for(response)
        return response

    @staticmethod
    def _refusal_for(response: httpx.Response) -> RefusalReceived:
        try:
            body = response.json()
        except ValueError as exc:
            raise RefusalReceived(
                "malformed",
                detail=f"HTTP {response.status_code} with no parseable Refusal body",
            ) from exc
        try:
            refusal = parse_strict(Refusal, body)
        except RefusalReceived as exc:
            return exc
        return RefusalReceived.from_refusal(refusal)
