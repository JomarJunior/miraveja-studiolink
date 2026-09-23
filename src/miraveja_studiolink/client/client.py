"""`StudioLinkClient`: the Studio end's ergonomic facade over one transport."""

from __future__ import annotations

import uuid
from datetime import datetime
from types import TracebackType

import httpx

from miraveja_studiolink.client import (
    candidates,
    comments,
    erasure,
    exhibition,
    experiences,
    images,
    presence,
    versions,
)
from miraveja_studiolink.client.transport import StudioLinkTransport
from miraveja_studiolink.messages.candidates import CandidateAccepted, Label
from miraveja_studiolink.messages.comments import CommentPublished
from miraveja_studiolink.messages.common import PersonaRef, Verdict
from miraveja_studiolink.messages.erasure import ErasureNoticeBatch
from miraveja_studiolink.messages.exhibition import ExhibitionView
from miraveja_studiolink.messages.experiences import ExperienceBatch
from miraveja_studiolink.messages.presence import PresenceState


class StudioLinkClient:
    """One Studio, one credential, one place its requests are made (R-9)."""

    def __init__(
        self,
        base_url: str,
        credential: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 35.0,
        allow_insecure: bool = False,
    ) -> None:
        self._transport = StudioLinkTransport(
            base_url,
            credential,
            transport=transport,
            timeout=timeout,
            allow_insecure=allow_insecure,
        )

    @property
    def transport(self) -> StudioLinkTransport:
        """The one chokepoint every request goes through — for callers needing raw access."""
        return self._transport

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> StudioLinkClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def supported_versions(self) -> list[str]:
        return await versions.supported_versions(self._transport)

    async def announce_presence(
        self, persona: PersonaRef, state: PresenceState, *, announced_at: datetime | None = None
    ) -> None:
        await presence.announce_presence(self._transport, persona, state, announced_at=announced_at)

    async def hand_over_candidate(
        self,
        *,
        send_mark: uuid.UUID,
        persona: PersonaRef,
        piece_id: uuid.UUID,
        title: str,
        statement: str,
        neutral_description: str,
        labels: list[Label],
        verdict: Verdict,
        image_bytes: bytes,
        image_media_type: str = "image/png",
    ) -> CandidateAccepted:
        return await candidates.hand_over_candidate(
            self._transport,
            send_mark=send_mark,
            persona=persona,
            piece_id=piece_id,
            title=title,
            statement=statement,
            neutral_description=neutral_description,
            labels=labels,
            verdict=verdict,
            image_bytes=image_bytes,
            image_media_type=image_media_type,
        )

    async def publish_comment(
        self,
        *,
        send_mark: uuid.UUID,
        persona: PersonaRef,
        text: str,
        verdict: Verdict,
        target_piece_id: uuid.UUID | None = None,
        target_comment_id: uuid.UUID | None = None,
        written_at: datetime | None = None,
    ) -> CommentPublished:
        return await comments.publish_comment(
            self._transport,
            send_mark=send_mark,
            persona=persona,
            text=text,
            verdict=verdict,
            target_piece_id=target_piece_id,
            target_comment_id=target_comment_id,
            written_at=written_at,
        )

    async def collect_experiences(
        self,
        persona_id: uuid.UUID,
        *,
        from_sequence: int | None = None,
        limit: int = 50,
        wait_seconds: int = 0,
    ) -> ExperienceBatch:
        return await experiences.collect_experiences(
            self._transport,
            persona_id,
            from_sequence=from_sequence,
            limit=limit,
            wait_seconds=wait_seconds,
        )

    async def acknowledge_experiences(self, persona_id: uuid.UUID, through_sequence: int) -> None:
        await experiences.acknowledge_experiences(self._transport, persona_id, through_sequence)

    async def collect_erasure_notices(
        self, persona_id: uuid.UUID, *, from_sequence: int | None = None, limit: int = 50
    ) -> ErasureNoticeBatch:
        return await erasure.collect_erasure_notices(
            self._transport, persona_id, from_sequence=from_sequence, limit=limit
        )

    async def acknowledge_erasure_notices(
        self, persona_id: uuid.UUID, through_sequence: int
    ) -> None:
        await erasure.acknowledge_erasure_notices(self._transport, persona_id, through_sequence)

    async def fetch_piece_image(self, piece_id: uuid.UUID) -> tuple[bytes, str]:
        return await images.fetch_piece_image(self._transport, piece_id)

    async def look_at_the_museum(
        self, as_persona_id: uuid.UUID, *, before: datetime | None = None, limit: int = 20
    ) -> ExhibitionView:
        return await exhibition.look_at_the_museum(
            self._transport, as_persona_id, before=before, limit=limit
        )
