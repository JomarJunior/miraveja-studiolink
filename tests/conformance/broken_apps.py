"""Deliberately broken Museum ends, built by swapping one handler in the real stand-in.

Used only to prove the conformance suite actually catches a violation (T027). Everything
except the one broken route behaves normally, reusing the real stand-in's handlers.
"""

from __future__ import annotations

import uuid

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from miraveja_studiolink.standin import app as standin_app
from miraveja_studiolink.standin.state import StandInState


def _swap(state: StandInState, path: str, endpoint) -> Starlette:
    routes = [
        Route(route.path, endpoint, methods=list(route.methods or []))
        if route.path == path
        else route
        for route in standin_app.routes
    ]
    app = Starlette(
        routes=routes, exception_handlers={standin_app.Refuse: standin_app._refuse_handler}
    )
    app.state.studiolink = state
    return app


def double_delivery_app(state: StandInState) -> Starlette:
    """Acknowledging experiences is a no-op: everything is delivered again forever."""

    async def fake_acknowledge(request: Request) -> Response:
        return Response(status_code=204)

    return _swap(
        state, "/studiolink/v1/personas/{personaId}/experiences/acknowledge", fake_acknowledge
    )


def missing_refusal_app(state: StandInState) -> Starlette:
    """Publishing a comment always succeeds, verdict or not."""

    async def fake_comments(request: Request) -> Response:
        return JSONResponse({"commentId": str(uuid.uuid4())}, status_code=201)

    return _swap(state, "/studiolink/v1/comments", fake_comments)
