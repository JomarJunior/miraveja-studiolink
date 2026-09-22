"""A scripted Studio that checks any Museum end without a Studio running (FR-037).

Every check here uses only the contract's own exchanges — nothing scripting-specific
the stand-in happens to offer — so the same suite runs unmodified against the reference
stand-in and against a real MuseuMusa. A handful of checks are opportunistic (they need
an exhibited piece to work with, which this suite cannot force a real Museum end to
create): those are reported as skipped, not failed, when the museum has nothing
exhibited yet.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import httpx

from miraveja_studiolink.client.client import StudioLinkClient
from miraveja_studiolink.client.transport import V1
from miraveja_studiolink.messages.common import PersonaRef, Verdict
from miraveja_studiolink.messages.refusal import RefusalReceived

_TINY_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


class Skip(Exception):
    """A check raises this to report 'inconclusive against this target', not a failure."""


def _synthetic_persona(label: str) -> PersonaRef:
    return PersonaRef(personaId=uuid.uuid4(), publicName=f"Synthetic Conformance Persona {label}")


def _accepted_verdict(scope: Literal["charter_and_quality", "hard_lines_only"]) -> Verdict:
    return Verdict(
        outcome="accepted",
        reason="Conformance check.",
        decidedAt=datetime.now(UTC),
        scope=scope,
    )


async def check_versions_carries_no_persona_data(client: StudioLinkClient) -> None:
    versions = await client.supported_versions()
    assert versions, "expected at least one supported version"
    assert all(isinstance(v, str) for v in versions)


async def check_presence_is_accepted(
    client: StudioLinkClient, persona: PersonaRef | None = None
) -> None:
    await client.announce_presence(persona or _synthetic_persona("Presence"), "in_the_studio")


async def check_candidate_goes_to_human_gate(client: StudioLinkClient) -> None:
    result = await client.hand_over_candidate(
        send_mark=uuid.uuid4(),
        persona=_synthetic_persona("Candidate"),
        piece_id=uuid.uuid4(),
        title="Conformance Check Piece",
        statement="A conformance check candidate.",
        neutral_description="A conformance check candidate.",
        labels=[],
        verdict=_accepted_verdict("charter_and_quality"),
        image_bytes=_TINY_PNG,
    )
    assert result.state == "with_the_human_gate", (
        f"candidate landed in state {result.state!r}, expected with_the_human_gate (FR-014)"
    )


async def check_candidate_sendmark_dedup(client: StudioLinkClient) -> None:
    persona = _synthetic_persona("Dedup")
    send_mark = uuid.uuid4()
    piece_id = uuid.uuid4()
    verdict = _accepted_verdict("charter_and_quality")

    first = await client.hand_over_candidate(
        send_mark=send_mark,
        persona=persona,
        piece_id=piece_id,
        title="Conformance Dedup Check",
        statement="statement",
        neutral_description="description",
        labels=[],
        verdict=verdict,
        image_bytes=_TINY_PNG,
    )
    second = await client.hand_over_candidate(
        send_mark=send_mark,
        persona=persona,
        piece_id=piece_id,
        title="Conformance Dedup Check",
        statement="statement",
        neutral_description="description",
        labels=[],
        verdict=verdict,
        image_bytes=_TINY_PNG,
    )
    assert first == second, (
        "resending the same sendMark did not return the original answer (FR-015)"
    )


async def check_comment_without_verdict_is_refused(
    client: StudioLinkClient, persona: PersonaRef | None = None
) -> None:
    persona = persona or _synthetic_persona("NoVerdict")
    try:
        await client.transport.request(
            "POST",
            f"{V1}/comments",
            json={
                "sendMark": str(uuid.uuid4()),
                "persona": {
                    "personaId": str(persona.personaId),
                    "publicName": persona.publicName,
                },
                "target": {"pieceId": str(uuid.uuid4())},
                "text": "Conformance check: this comment carries no verdict.",
                "writtenAt": datetime.now(UTC).isoformat(),
            },
        )
    except RefusalReceived:
        return
    raise AssertionError("a comment with no verdict was accepted (FR-027)")


async def check_unsupported_version_is_refused_first(client: StudioLinkClient) -> None:
    try:
        await client.transport.request(
            "GET",
            "/studiolink/v99/exhibition",
            params={"asPersonaId": str(uuid.uuid4())},
        )
    except RefusalReceived as exc:
        assert exc.reason == "unsupported_version", (
            f"expected unsupported_version, got {exc.reason}"
        )
        assert exc.supported_versions, "refusal did not name the supported versions (FR-006)"
        return
    raise AssertionError("an unsupported contract version was not refused (FR-005, FR-006)")


async def check_experiences_never_redeliver_after_acknowledgement(
    client: StudioLinkClient, persona: PersonaRef | None = None
) -> None:
    persona = persona or _synthetic_persona("Experiences")
    await client.announce_presence(persona, "in_the_studio")
    batch = await client.collect_experiences(persona.personaId, limit=100)
    assert batch.nextSequence is None or isinstance(batch.nextSequence, int)
    if not batch.items:
        raise Skip("no experiences waiting for a brand-new persona to check redelivery with")
    last_sequence = batch.items[-1].sequence
    await client.acknowledge_experiences(persona.personaId, last_sequence)
    again = await client.collect_experiences(persona.personaId, limit=100)
    assert all(item.sequence > last_sequence for item in again.items), (
        "an acknowledged experience was delivered again (FR-019)"
    )


async def check_erasure_notices_are_collectable_on_their_own(client: StudioLinkClient) -> None:
    persona = _synthetic_persona("Erasure")
    await client.announce_presence(persona, "in_the_studio")
    batch = await client.collect_erasure_notices(persona.personaId)
    assert isinstance(batch.items, list)


async def check_exhibition_view_is_time_ordered(client: StudioLinkClient) -> None:
    persona = _synthetic_persona("Looking")
    await client.announce_presence(persona, "in_the_studio")
    view = await client.look_at_the_museum(persona.personaId, limit=50)
    timestamps = [piece.exhibitedAt for piece in view.pieces]
    assert timestamps == sorted(timestamps, reverse=True), (
        "the exhibition view was not ordered by time, most recent first (FR-041)"
    )


async def check_unknown_piece_image_is_refused(client: StudioLinkClient) -> None:
    try:
        await client.fetch_piece_image(uuid.uuid4())
    except RefusalReceived:
        return
    raise AssertionError("fetching an unknown piece's image was not refused (FR-040a)")


async def check_comment_publish_succeeds_on_an_existing_piece(client: StudioLinkClient) -> None:
    persona = _synthetic_persona("Replying")
    await client.announce_presence(persona, "in_the_studio")
    view = await client.look_at_the_museum(persona.personaId, limit=1)
    if not view.pieces:
        raise Skip("no exhibited piece is available on this target to comment on")
    piece = view.pieces[0]
    await client.publish_comment(
        send_mark=uuid.uuid4(),
        persona=persona,
        text="A conformance check reply.",
        verdict=_accepted_verdict("hard_lines_only"),
        target_piece_id=piece.pieceId,
    )


CheckFn = Callable[[StudioLinkClient], Awaitable[None]]

CHECKS: list[tuple[str, CheckFn]] = [
    ("supportedVersions carries no persona data (FR-007)", check_versions_carries_no_persona_data),
    ("a presence announcement is accepted (FR-009)", check_presence_is_accepted),
    (
        "an accepted candidate goes to the human gate, never exhibition (FR-014)",
        check_candidate_goes_to_human_gate,
    ),
    (
        "resending a candidate under the same sendMark returns the original answer (FR-015)",
        check_candidate_sendmark_dedup,
    ),
    ("a comment with no verdict is refused (FR-027)", check_comment_without_verdict_is_refused),
    (
        "an unsupported version is refused before content is acted on (FR-005, FR-006)",
        check_unsupported_version_is_refused_first,
    ),
    (
        "experiences are never redelivered once acknowledged (FR-016, FR-018, FR-019)",
        check_experiences_never_redeliver_after_acknowledgement,
    ),
    (
        "erasure notices are collectable on their own cursor (FR-045)",
        check_erasure_notices_are_collectable_on_their_own,
    ),
    ("the exhibition view is ordered by time (FR-041)", check_exhibition_view_is_time_ordered),
    (
        "fetching an unknown piece's image is refused (FR-040a)",
        check_unknown_piece_image_is_refused,
    ),
    (
        "a well-formed reply is published when a target exists (FR-025 to FR-027)",
        check_comment_publish_succeeds_on_an_existing_piece,
    ),
]


@dataclass
class CheckResult:
    name: str
    status: Literal["pass", "fail", "skip"]
    detail: str | None = None


@dataclass
class ConformanceReport:
    results: list[CheckResult]

    @property
    def all_passed(self) -> bool:
        return all(result.status != "fail" for result in self.results)

    def print_summary(self) -> None:
        symbols = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}
        for result in self.results:
            line = f"[{symbols[result.status]}] {result.name}"
            if result.detail:
                line += f" — {result.detail}"
            print(line)
        passed = sum(1 for r in self.results if r.status == "pass")
        failed = sum(1 for r in self.results if r.status == "fail")
        skipped = sum(1 for r in self.results if r.status == "skip")
        print(f"\n{passed} passed, {failed} failed, {skipped} skipped ({len(self.results)} total)")


async def _run_one(name: str, check: CheckFn, client: StudioLinkClient) -> CheckResult:
    try:
        await check(client)
    except Skip as exc:
        return CheckResult(name, "skip", str(exc) or None)
    except Exception as exc:
        return CheckResult(name, "fail", f"{type(exc).__name__}: {exc}")
    return CheckResult(name, "pass")


async def run_suite_async(
    base_url: str, credential: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> ConformanceReport:
    async with StudioLinkClient(base_url, credential, transport=transport) as client:
        results = [await _run_one(name, check, client) for name, check in CHECKS]
    return ConformanceReport(results)


def run_suite(
    base_url: str, credential: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> ConformanceReport:
    return asyncio.run(run_suite_async(base_url, credential, transport=transport))
