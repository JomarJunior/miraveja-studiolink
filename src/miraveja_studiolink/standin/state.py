"""In-memory Museum-side state for the reference stand-in (FR-036).

Everything here is the stand-in's own bookkeeping, not wire messages: PieceRecord and
CommentRecord carry internal fields (like a visitor's raw scripting id) that never cross
the Studio Link, alongside what a real Museum end would need to answer every exchange in
the contract without MuseuMusa or PortaGuarda.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal

DEFAULT_STALENESS_WINDOW = timedelta(hours=2)


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class QueueItem[ItemT]:
    sequence: int
    payload: ItemT
    withdrawn: bool = False
    acknowledged: bool = False


class PersonaQueue[ItemT]:
    """A held, per-persona queue: at-least-once, oldest first, its own cursor (R-4)."""

    def __init__(self) -> None:
        self._items: list[QueueItem[ItemT]] = []
        self._next_sequence = 1
        self._acknowledged_through = 0
        self._condition = asyncio.Condition()

    async def append(self, payload: ItemT) -> int:
        async with self._condition:
            sequence = self._next_sequence
            self._next_sequence += 1
            self._items.append(QueueItem(sequence=sequence, payload=payload))
            self._condition.notify_all()
            return sequence

    def withdraw(self, matches: Callable[[ItemT], bool]) -> None:
        for item in self._items:
            if not item.acknowledged and matches(item.payload):
                item.withdrawn = True

    def _pending(self, start: int) -> list[QueueItem[ItemT]]:
        return sorted(
            (
                item
                for item in self._items
                if item.sequence >= start and not item.withdrawn and not item.acknowledged
            ),
            key=lambda item: item.sequence,
        )

    async def collect(
        self, from_sequence: int | None, limit: int, wait_seconds: float
    ) -> tuple[list[QueueItem[ItemT]], int | None]:
        start = from_sequence if from_sequence is not None else self._acknowledged_through + 1
        deadline = time.monotonic() + wait_seconds
        async with self._condition:
            pending = self._pending(start)
            while not pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    await asyncio.wait_for(self._condition.wait(), timeout=remaining)
                except TimeoutError:
                    break
                pending = self._pending(start)
        page = pending[:limit]
        next_sequence = page[-1].sequence + 1 if len(pending) > len(page) else None
        return page, next_sequence

    def acknowledge(self, through_sequence: int) -> None:
        self._acknowledged_through = max(self._acknowledged_through, through_sequence)
        for item in self._items:
            if item.sequence <= through_sequence:
                item.acknowledged = True


@dataclass
class PersonaRecord:
    persona_id: uuid.UUID
    public_name: str
    presence_state: Literal["in_the_studio", "away", "resting"] = "away"
    announced_at: datetime | None = None
    last_seen_at: datetime | None = None


@dataclass
class VisitorRecord:
    visitor_id: str
    display_name: str
    erased: bool = False


@dataclass
class CommentRecord:
    comment_id: uuid.UUID
    piece_id: uuid.UUID
    text: str
    written_at: datetime
    author_persona_id: uuid.UUID | None
    author_visitor_id: str | None
    reply_to_comment_id: uuid.UUID | None = None
    send_mark: uuid.UUID | None = None


@dataclass
class PieceRecord:
    piece_id: uuid.UUID
    owner_persona_id: uuid.UUID
    title: str
    statement: str
    neutral_description: str
    labels: list[str]
    image_bytes: bytes
    image_media_type: str
    state: Literal["with_the_human_gate", "exhibited", "declined", "taken_down"] = (
        "with_the_human_gate"
    )
    exhibited_at: datetime | None = None
    send_mark: uuid.UUID | None = None
    comment_ids: list[uuid.UUID] = field(default_factory=list)


class StandInState:
    """Everything the reference Museum end needs to answer the Studio Link, in memory."""

    def __init__(
        self, credential: str, *, staleness_window: timedelta = DEFAULT_STALENESS_WINDOW
    ) -> None:
        self.credential = credential
        self.staleness_window = staleness_window

        self.personas: dict[uuid.UUID, PersonaRecord] = {}
        self.visitors: dict[str, VisitorRecord] = {}
        self.pieces: dict[uuid.UUID, PieceRecord] = {}
        self.comments: dict[uuid.UUID, CommentRecord] = {}

        self._candidate_responses: dict[uuid.UUID, dict] = {}
        self._comment_responses: dict[uuid.UUID, dict] = {}

        self.experience_queues: dict[uuid.UUID, PersonaQueue[dict]] = {}
        self.erasure_queues: dict[uuid.UUID, PersonaQueue[dict]] = {}

        self._closed_conversations: set[tuple[uuid.UUID, str]] = set()
        self._visitor_personas: dict[str, set[uuid.UUID]] = {}
        self._pseudonym_secret = secrets.token_bytes(32)

        self._forced_responses: dict[str, object] = {}

    # -- test-only response forcing (T023, User Story 2) ---------------------------

    def force_response(self, operation: str, body: object) -> None:
        """Make the next call to `operation` answer with `body` verbatim.

        Exists so contract tests can hand the Studio end a deliberately contaminated
        message (FR-021 to FR-023) without the stand-in's own logic ever being able to
        construct one. Not part of the contract; a testing-only escape hatch.
        """
        self._forced_responses[operation] = body

    def take_forced_response(self, operation: str) -> object | None:
        return self._forced_responses.pop(operation, None)

    # -- personas -----------------------------------------------------------------

    def register_persona(self, persona_id: uuid.UUID, public_name: str) -> PersonaRecord:
        record = self.personas.get(persona_id)
        if record is None:
            record = PersonaRecord(persona_id=persona_id, public_name=public_name)
            self.personas[persona_id] = record
            self.experience_queues[persona_id] = PersonaQueue()
            self.erasure_queues[persona_id] = PersonaQueue()
        else:
            record.public_name = public_name
        return record

    def is_known_persona(self, persona_id: uuid.UUID) -> bool:
        return persona_id in self.personas

    def presence_of(self, persona_id: uuid.UUID) -> Literal["in_the_studio", "away", "resting"]:
        record = self.personas[persona_id]
        if record.last_seen_at is None:
            return "away"
        if utcnow() - record.last_seen_at > self.staleness_window:
            return "away"
        return record.presence_state

    def announce_presence(
        self, persona_id: uuid.UUID, public_name: str, state: str, announced_at: datetime
    ) -> None:
        record = self.register_persona(persona_id, public_name)
        record.presence_state = state  # type: ignore[assignment]
        record.announced_at = announced_at
        record.last_seen_at = utcnow()

    # -- pseudonyms (R-6, FR-017, FR-017a) -----------------------------------------

    def pseudonym_for(self, persona_id: uuid.UUID, visitor_id: str) -> str:
        digest = hmac.new(
            self._pseudonym_secret,
            f"{persona_id}:{visitor_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        self._visitor_personas.setdefault(visitor_id, set()).add(persona_id)
        return f"v-{digest[:20]}"

    def visitor_ref(self, persona_id: uuid.UUID, visitor_id: str) -> dict:
        visitor = self.visitors[visitor_id]
        return {
            "pseudonym": self.pseudonym_for(persona_id, visitor_id),
            "displayName": None if visitor.erased else visitor.display_name,
        }

    # -- scripting (FR-036) --------------------------------------------------------

    def add_visitor(self, visitor_id: str, display_name: str) -> None:
        self.visitors[visitor_id] = VisitorRecord(visitor_id=visitor_id, display_name=display_name)

    def close_conversation(self, persona_id: uuid.UUID, visitor_id: str) -> None:
        """A visitor stopped interacting with a persona (Charter 7.2)."""
        self._closed_conversations.add((persona_id, visitor_id))

    def is_conversation_closed(self, persona_id: uuid.UUID, visitor_id: str) -> bool:
        return (persona_id, visitor_id) in self._closed_conversations

    async def erase_visitor(self, visitor_id: str) -> None:
        visitor = self.visitors[visitor_id]
        visitor.erased = True
        for persona_id in self._visitor_personas.get(visitor_id, set()):
            pseudonym = self.pseudonym_for(persona_id, visitor_id)
            await self.erasure_queues[persona_id].append({"pseudonym": pseudonym})

    async def seed_exhibited_piece(
        self,
        *,
        piece_id: uuid.UUID,
        persona_id: uuid.UUID,
        public_name: str,
        title: str,
        statement: str,
        neutral_description: str,
        labels: list[str] | None = None,
        image_bytes: bytes = b"\x89PNG\r\n",
        image_media_type: str = "image/png",
        exhibited_at: datetime | None = None,
    ) -> None:
        self.register_persona(persona_id, public_name)
        self.pieces[piece_id] = PieceRecord(
            piece_id=piece_id,
            owner_persona_id=persona_id,
            title=title,
            statement=statement,
            neutral_description=neutral_description,
            labels=labels or [],
            image_bytes=image_bytes,
            image_media_type=image_media_type,
            state="exhibited",
            exhibited_at=exhibited_at or utcnow(),
        )

    async def script_comment(
        self,
        *,
        piece_id: uuid.UUID,
        visitor_id: str,
        text: str,
        written_at: datetime | None = None,
        reply_to_comment_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        piece = self.pieces[piece_id]
        comment_id = uuid.uuid4()
        record = CommentRecord(
            comment_id=comment_id,
            piece_id=piece_id,
            text=text,
            written_at=written_at or utcnow(),
            author_persona_id=None,
            author_visitor_id=visitor_id,
            reply_to_comment_id=reply_to_comment_id,
        )
        self.comments[comment_id] = record
        piece.comment_ids.append(comment_id)
        author = self.visitor_ref(piece.owner_persona_id, visitor_id)
        payload = {
            "kind": "comment",
            "occurredAt": record.written_at,
            "commentId": comment_id,
            "author": author,
            "text": text,
        }
        # Exactly one of these, per data-model.md; the other is omitted, not null,
        # since neither is required by the hub schema (FR-016).
        if reply_to_comment_id is not None:
            payload["inReplyToCommentId"] = reply_to_comment_id
        else:
            payload["onPieceId"] = piece_id
        await self.experience_queues[piece.owner_persona_id].append(payload)
        return comment_id

    async def script_reaction(self, *, piece_id: uuid.UUID, visitor_id: str, reaction: str) -> None:
        piece = self.pieces[piece_id]
        payload = {
            "kind": "reaction",
            "occurredAt": utcnow(),
            "visitor": self.visitor_ref(piece.owner_persona_id, visitor_id),
            "reaction": reaction,
            "onPieceId": piece_id,
        }
        await self.experience_queues[piece.owner_persona_id].append(payload)

    async def simulate_gate_outcome(
        self,
        piece_id: uuid.UUID,
        outcome: Literal["exhibited", "declined", "taken_down"],
        reason: str | None = None,
    ) -> None:
        piece = self.pieces[piece_id]
        piece.state = outcome
        if outcome == "exhibited":
            piece.exhibited_at = utcnow()
        payload = {
            "kind": "gate_outcome",
            "occurredAt": utcnow(),
            "pieceId": piece_id,
            "outcome": outcome,
            "reason": reason,
        }
        await self.experience_queues[piece.owner_persona_id].append(payload)

    # -- send-mark dedup (FR-015, FR-031, FR-031a) ---------------------------------

    def candidate_response_for(self, send_mark: uuid.UUID) -> dict | None:
        return self._candidate_responses.get(send_mark)

    def remember_candidate_response(self, send_mark: uuid.UUID, response: dict) -> None:
        self._candidate_responses[send_mark] = response

    def comment_response_for(self, send_mark: uuid.UUID) -> dict | None:
        return self._comment_responses.get(send_mark)

    def remember_comment_response(self, send_mark: uuid.UUID, response: dict) -> None:
        self._comment_responses[send_mark] = response

    def inspect(self) -> dict:
        """Everything the Studio has sent, for test assertions (FR-036)."""
        return {
            "personas": dict(self.personas),
            "pieces": dict(self.pieces),
            "comments": dict(self.comments),
            "candidate_send_marks": sorted(self._candidate_responses),
            "comment_send_marks": sorted(self._comment_responses),
        }

    def reset(self) -> None:
        self.personas.clear()
        self.visitors.clear()
        self.pieces.clear()
        self.comments.clear()
        self._candidate_responses.clear()
        self._comment_responses.clear()
        self.experience_queues.clear()
        self.erasure_queues.clear()
        self._closed_conversations.clear()
        self._visitor_personas.clear()
