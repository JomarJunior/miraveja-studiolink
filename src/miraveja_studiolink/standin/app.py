"""The reference Museum end: an in-memory ASGI app conforming to the Studio Link (FR-036).

Runs with no MuseuMusa or PortaGuarda. Every path in `studiolink-v1.yaml` is served here,
using the same closed Pydantic models the client uses, so a request with an unknown field
is refused the same way on both ends (FR-023).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from miraveja_studiolink.messages.candidates import Candidate, CandidateAccepted
from miraveja_studiolink.messages.classify import classify_validation_error
from miraveja_studiolink.messages.comments import (
    CommentPublished,
    PersonaComment,
    PieceTarget,
)
from miraveja_studiolink.messages.common import Acknowledgement
from miraveja_studiolink.messages.erasure import ErasureNoticeBatch
from miraveja_studiolink.messages.exhibition import ExhibitionView
from miraveja_studiolink.messages.experiences import ExperienceBatch
from miraveja_studiolink.messages.presence import PresenceAnnouncement
from miraveja_studiolink.messages.refusal import RefusalReason
from miraveja_studiolink.standin.state import CommentRecord, PieceRecord, StandInState

SUPPORTED_CONTRACT_VERSIONS = ["1.0.0"]
MAX_IMAGE_BYTES = 20 * 1024 * 1024


class Refuse(Exception):
    """Raised by a handler to answer with the Refused response (R-10)."""

    def __init__(
        self,
        reason: RefusalReason,
        status_code: int,
        *,
        detail: str | None = None,
        supported_versions: list[str] | None = None,
    ) -> None:
        self.reason = reason
        self.status_code = status_code
        self.detail = detail
        self.supported_versions = supported_versions
        super().__init__(reason)


async def _refuse_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, Refuse)
    body: dict[str, Any] = {"reason": exc.reason}
    if exc.detail is not None:
        body["detail"] = exc.detail
    if exc.supported_versions is not None:
        body["supportedVersions"] = exc.supported_versions
    return JSONResponse(body, status_code=exc.status_code)


def _state(request: Request) -> StandInState:
    return request.app.state.studiolink  # type: ignore[no-any-return]


def _require_auth(request: Request, state: StandInState) -> None:
    header = request.headers.get("authorization", "")
    if header != f"Bearer {state.credential}":
        raise Refuse("not_authenticated", 401)


def _require_known_persona(state: StandInState, persona_id: uuid.UUID) -> None:
    if not state.is_known_persona(persona_id):
        raise Refuse("persona_not_recognized", 404)


def _parse_or_refuse[T](model: type[T], data: object, *, status_code: int = 400) -> T:
    try:
        return model.model_validate(data)  # type: ignore[attr-defined,no-any-return]
    except ValidationError as exc:
        reason = classify_validation_error(exc)
        raise Refuse(reason, status_code, detail=str(exc)) from exc


async def _read_json_or_refuse(request: Request) -> object:
    try:
        return await request.json()
    except json.JSONDecodeError as exc:
        raise Refuse("malformed", 400, detail="request body is not valid JSON") from exc


def _uuid_or_refuse(raw: str, reason: RefusalReason = "malformed") -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise Refuse(reason, 404 if reason != "malformed" else 400) from exc


def _with_sequence(payload: dict, sequence: int) -> dict:
    return {**payload, "sequence": sequence}


# -- handlers -----------------------------------------------------------------------


async def versions_handler(request: Request) -> JSONResponse:
    return JSONResponse({"supportedVersions": SUPPORTED_CONTRACT_VERSIONS})


async def presence_handler(request: Request) -> Response:
    state = _state(request)
    _require_auth(request, state)
    body = await _read_json_or_refuse(request)
    announcement = _parse_or_refuse(PresenceAnnouncement, body)
    state.announce_presence(
        announcement.persona.personaId,
        announcement.persona.publicName,
        announcement.state,
        announcement.announcedAt,
    )
    return Response(status_code=204)


async def candidates_handler(request: Request) -> Response:
    state = _state(request)
    _require_auth(request, state)
    form = await request.form()
    candidate_part = form.get("candidate")
    image_part = form.get("image")
    if candidate_part is None or image_part is None:
        raise Refuse("malformed", 400, detail="candidate and image parts are both required")
    if not isinstance(image_part, UploadFile):
        raise Refuse("malformed", 400, detail="image part must be a file")

    raw = await candidate_part.read() if isinstance(candidate_part, UploadFile) else candidate_part
    try:
        candidate_data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise Refuse("malformed", 400, detail="candidate part is not valid JSON") from exc
    candidate = _parse_or_refuse(Candidate, candidate_data)

    existing = state.candidate_response_for(candidate.sendMark)
    if existing is not None:
        return JSONResponse(existing, status_code=202)

    image_bytes = await image_part.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise Refuse("malformed", 413, detail="image exceeds 20 MB")

    state.register_persona(candidate.persona.personaId, candidate.persona.publicName)
    state.pieces[candidate.pieceId] = PieceRecord(
        piece_id=candidate.pieceId,
        owner_persona_id=candidate.persona.personaId,
        title=candidate.title,
        statement=candidate.statement,
        neutral_description=candidate.neutralDescription,
        labels=list(candidate.labels),
        image_bytes=image_bytes,
        image_media_type=image_part.content_type or "image/png",
        send_mark=candidate.sendMark,
    )
    response_body = CandidateAccepted(
        pieceId=candidate.pieceId, state="with_the_human_gate"
    ).model_dump(mode="json")
    state.remember_candidate_response(candidate.sendMark, response_body)
    return JSONResponse(response_body, status_code=202)


async def comments_handler(request: Request) -> Response:
    state = _state(request)
    _require_auth(request, state)
    body = await _read_json_or_refuse(request)
    comment = _parse_or_refuse(PersonaComment, body)

    existing = state.comment_response_for(comment.sendMark)
    if existing is not None:
        return JSONResponse(existing, status_code=201)

    state.register_persona(comment.persona.personaId, comment.persona.publicName)

    reply_to: uuid.UUID | None = None
    target = comment.target
    if isinstance(target, PieceTarget):
        piece_id = target.pieceId
    else:
        parent = state.comments.get(target.commentId)
        if parent is None:
            raise Refuse("piece_not_on_display", 404, detail="replied-to comment does not exist")
        piece_id = parent.piece_id
        reply_to = parent.comment_id
        if parent.author_visitor_id is not None and state.is_conversation_closed(
            comment.persona.personaId, parent.author_visitor_id
        ):
            raise Refuse("conversation_closed", 403)

    piece = state.pieces.get(piece_id)
    if piece is None or piece.state != "exhibited":
        raise Refuse("piece_not_on_display", 404)

    comment_id = uuid.uuid4()
    record = CommentRecord(
        comment_id=comment_id,
        piece_id=piece_id,
        text=comment.text,
        written_at=comment.writtenAt,
        author_persona_id=comment.persona.personaId,
        author_visitor_id=None,
        reply_to_comment_id=reply_to,
        send_mark=comment.sendMark,
    )
    state.comments[comment_id] = record
    piece.comment_ids.append(comment_id)

    if piece.owner_persona_id != comment.persona.personaId:
        payload = {
            "kind": "comment",
            "occurredAt": record.written_at,
            "commentId": comment_id,
            "author": {
                "personaId": comment.persona.personaId,
                "publicName": comment.persona.publicName,
            },
            "text": comment.text,
        }
        if reply_to is not None:
            payload["inReplyToCommentId"] = reply_to
        else:
            payload["onPieceId"] = piece_id
        await state.experience_queues[piece.owner_persona_id].append(payload)

    response_body = CommentPublished(commentId=comment_id).model_dump(mode="json")
    state.remember_comment_response(comment.sendMark, response_body)
    return JSONResponse(response_body, status_code=201)


async def collect_experiences_handler(request: Request) -> JSONResponse:
    state = _state(request)
    _require_auth(request, state)
    persona_id = _uuid_or_refuse(request.path_params["personaId"], "persona_not_recognized")
    _require_known_persona(state, persona_id)

    from_sequence_raw = request.query_params.get("fromSequence")
    from_sequence = int(from_sequence_raw) if from_sequence_raw is not None else None
    limit = int(request.query_params.get("limit", 50))
    wait_seconds = float(request.query_params.get("waitSeconds", 0))

    items, next_sequence = await state.experience_queues[persona_id].collect(
        from_sequence, limit, wait_seconds
    )
    batch = ExperienceBatch.model_validate(
        {
            "items": [_with_sequence(item.payload, item.sequence) for item in items],
            "nextSequence": next_sequence,
        }
    )
    return JSONResponse(batch.model_dump(mode="json", exclude_unset=True))


async def acknowledge_experiences_handler(request: Request) -> Response:
    state = _state(request)
    _require_auth(request, state)
    persona_id = _uuid_or_refuse(request.path_params["personaId"], "persona_not_recognized")
    _require_known_persona(state, persona_id)
    body = await _read_json_or_refuse(request)
    ack = _parse_or_refuse(Acknowledgement, body)
    state.experience_queues[persona_id].acknowledge(ack.throughSequence)
    return Response(status_code=204)


async def collect_erasure_notices_handler(request: Request) -> JSONResponse:
    state = _state(request)
    _require_auth(request, state)
    persona_id = _uuid_or_refuse(request.path_params["personaId"], "persona_not_recognized")
    _require_known_persona(state, persona_id)

    from_sequence_raw = request.query_params.get("fromSequence")
    from_sequence = int(from_sequence_raw) if from_sequence_raw is not None else None
    limit = int(request.query_params.get("limit", 50))

    items, next_sequence = await state.erasure_queues[persona_id].collect(from_sequence, limit, 0)
    batch = ErasureNoticeBatch.model_validate(
        {
            "items": [_with_sequence(item.payload, item.sequence) for item in items],
            "nextSequence": next_sequence,
        }
    )
    return JSONResponse(batch.model_dump(mode="json", exclude_unset=True))


async def acknowledge_erasure_notices_handler(request: Request) -> Response:
    state = _state(request)
    _require_auth(request, state)
    persona_id = _uuid_or_refuse(request.path_params["personaId"], "persona_not_recognized")
    _require_known_persona(state, persona_id)
    body = await _read_json_or_refuse(request)
    ack = _parse_or_refuse(Acknowledgement, body)
    state.erasure_queues[persona_id].acknowledge(ack.throughSequence)
    return Response(status_code=204)


async def fetch_piece_image_handler(request: Request) -> Response:
    state = _state(request)
    _require_auth(request, state)
    piece_id = _uuid_or_refuse(request.path_params["pieceId"], "piece_not_on_display")
    piece = state.pieces.get(piece_id)
    if piece is None:
        raise Refuse("piece_not_on_display", 404)
    return Response(content=piece.image_bytes, media_type=piece.image_media_type)


async def look_at_the_museum_handler(request: Request) -> JSONResponse:
    state = _state(request)
    _require_auth(request, state)
    as_persona_raw = request.query_params.get("asPersonaId")
    if not as_persona_raw:
        raise Refuse("malformed", 400, detail="asPersonaId is required")
    as_persona_id = _uuid_or_refuse(as_persona_raw)
    _require_known_persona(state, as_persona_id)

    before_raw = request.query_params.get("before")
    before = datetime.fromisoformat(before_raw) if before_raw else None
    limit = int(request.query_params.get("limit", 20))

    def exhibited_at(piece: PieceRecord) -> datetime:
        assert piece.exhibited_at is not None  # always set alongside state == "exhibited"
        return piece.exhibited_at

    candidates = [
        piece
        for piece in state.pieces.values()
        if piece.state == "exhibited" and (before is None or exhibited_at(piece) < before)
    ]
    candidates.sort(key=exhibited_at, reverse=True)
    page = candidates[:limit]
    has_more = len(candidates) > len(page)
    next_before = exhibited_at(page[-1]) if page and has_more else None

    def author_ref(comment: CommentRecord) -> dict:
        if comment.author_persona_id is not None:
            owner = state.personas[comment.author_persona_id]
            return {"personaId": owner.persona_id, "publicName": owner.public_name}
        assert comment.author_visitor_id is not None
        return state.visitor_ref(as_persona_id, comment.author_visitor_id)

    pieces_payload = []
    for piece in page:
        conversation = sorted(
            (state.comments[cid] for cid in piece.comment_ids), key=lambda c: c.written_at
        )
        pieces_payload.append(
            {
                "pieceId": piece.piece_id,
                "persona": {
                    "personaId": piece.owner_persona_id,
                    "publicName": state.personas[piece.owner_persona_id].public_name,
                },
                "title": piece.title,
                "statement": piece.statement,
                "neutralDescription": piece.neutral_description,
                "labels": piece.labels,
                "imageMediaType": piece.image_media_type,
                "exhibitedAt": exhibited_at(piece),
                "conversation": [
                    {
                        "commentId": c.comment_id,
                        "author": author_ref(c),
                        "text": c.text,
                        "writtenAt": c.written_at,
                    }
                    for c in conversation
                ],
            }
        )

    view = ExhibitionView.model_validate({"pieces": pieces_payload, "nextBefore": next_before})
    return JSONResponse(view.model_dump(mode="json", exclude_unset=True))


async def unsupported_version_handler(request: Request) -> Response:
    version = request.path_params.get("version")
    if version == "v1":
        return Response(status_code=404)
    return JSONResponse(
        {"reason": "unsupported_version", "supportedVersions": SUPPORTED_CONTRACT_VERSIONS},
        status_code=400,
    )


routes = [
    Route("/studiolink/versions", versions_handler, methods=["GET"]),
    Route("/studiolink/v1/presence", presence_handler, methods=["POST"]),
    Route("/studiolink/v1/candidates", candidates_handler, methods=["POST"]),
    Route("/studiolink/v1/comments", comments_handler, methods=["POST"]),
    Route(
        "/studiolink/v1/personas/{personaId}/experiences",
        collect_experiences_handler,
        methods=["GET"],
    ),
    Route(
        "/studiolink/v1/personas/{personaId}/experiences/acknowledge",
        acknowledge_experiences_handler,
        methods=["POST"],
    ),
    Route(
        "/studiolink/v1/personas/{personaId}/erasure-notices",
        collect_erasure_notices_handler,
        methods=["GET"],
    ),
    Route(
        "/studiolink/v1/personas/{personaId}/erasure-notices/acknowledge",
        acknowledge_erasure_notices_handler,
        methods=["POST"],
    ),
    Route("/studiolink/v1/pieces/{pieceId}/image", fetch_piece_image_handler, methods=["GET"]),
    Route("/studiolink/v1/exhibition", look_at_the_museum_handler, methods=["GET"]),
    Route(
        "/studiolink/{version}/{rest:path}",
        unsupported_version_handler,
        methods=["GET", "POST"],
    ),
]


def create_app(state: StandInState) -> Starlette:
    app = Starlette(routes=routes, exception_handlers={Refuse: _refuse_handler})
    app.state.studiolink = state
    return app
