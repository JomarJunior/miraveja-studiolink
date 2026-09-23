"""The Studio credential is never sent in clear (R-9).

The credential identifies the whole Studio, so a mistyped base URL must fail loudly
rather than quietly leak it on the first request.
"""

from __future__ import annotations

import pytest

from miraveja_studiolink.client.client import StudioLinkClient


def test_plain_http_to_a_remote_host_is_refused() -> None:
    with pytest.raises(ValueError, match="refusing to send the Studio credential"):
        StudioLinkClient("http://museum.example", "super-secret-token")


def test_https_is_accepted() -> None:
    client = StudioLinkClient("https://museum.example", "super-secret-token")
    assert client.transport is not None


@pytest.mark.parametrize("base_url", ["http://localhost:8080", "http://127.0.0.1:8080"])
def test_loopback_is_accepted(base_url: str) -> None:
    """A local stand-in has no network hop for the credential to cross."""
    client = StudioLinkClient(base_url, "dev-token")
    assert client.transport is not None


def test_a_trusted_private_link_can_opt_out() -> None:
    client = StudioLinkClient("http://museum.internal", "token", allow_insecure=True)
    assert client.transport is not None


def test_an_injected_transport_skips_the_check() -> None:
    """Tests drive an ASGI app directly; there is no socket and so no exposure."""
    import httpx

    from miraveja_studiolink.standin.app import create_app
    from miraveja_studiolink.standin.state import StandInState

    app = create_app(StandInState("t"))
    client = StudioLinkClient("http://standin", "t", transport=httpx.ASGITransport(app=app))
    assert client.transport is not None
