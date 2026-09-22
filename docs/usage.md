# Usage

Two audiences use this library: a Studio component (**🎭 SonaVida**, in Stage A) that
speaks *for* a persona, and a Museum end (**🏛️ MuseuMusa**, in Stage B) that gets
checked against the contract. Both are covered below. See
[`specs/001-studiolink-contract/`](https://github.com/JomarJunior/miraveja-ecosystem/tree/main/specs/001-studiolink-contract)
in the hub for the contract itself and the rules behind every choice here.

## How a Studio component talks to the Museum side

Everything goes through one `StudioLinkClient`, which is async (a collection can long-poll
for up to 30 seconds, and nothing should block the rest of the Studio while it waits):

```python
import asyncio
import uuid
from datetime import UTC, datetime

from miraveja_studiolink.client import StudioLinkClient
from miraveja_studiolink.messages.common import PersonaRef, Verdict
from miraveja_studiolink.messages.refusal import RefusalReceived


async def main() -> None:
    persona = PersonaRef(personaId=uuid.UUID("..."), publicName="...")

    async with StudioLinkClient("https://museum.example", credential="...") as client:
        # Tell the Museum side the persona is here (FR-009).
        await client.announce_presence(persona, "in_the_studio")

        # Collect what happened while the persona was away, oldest first (FR-016 to FR-019).
        batch = await client.collect_experiences(persona.personaId, limit=100, wait_seconds=30)
        for experience in batch.items:
            ...  # hand each one to the persona's own memory, one at a time
        if batch.items:
            await client.acknowledge_experiences(persona.personaId, batch.items[-1].sequence)

        # Hand over a candidate that passed the AI gate (FR-012 to FR-015).
        await client.hand_over_candidate(
            send_mark=uuid.uuid4(),  # reused unchanged if this exact hand-over is retried
            persona=persona,
            piece_id=uuid.uuid4(),
            title="...",
            statement="...",  # the persona's own voice
            neutral_description="...",  # from DescriDiva
            labels=[],  # "explicit" and/or "violence", or empty
            verdict=Verdict(
                outcome="accepted",
                reason="...",
                decidedAt=datetime.now(UTC),
                scope="charter_and_quality",
            ),
            image_bytes=b"...",
        )


asyncio.run(main())
```

**Every call can raise `RefusalReceived`.** That is not a bug path to work around; it is
the contract's only error shape, and it covers two different situations the same way:

- the Museum side refused the request (a closed, machine-readable `reason` — see
  `miraveja_studiolink.messages.refusal.RefusalReason` for the full list);
- the response looked fine on the wire but carried a field the contract does not
  define, and the client refused to trust any of it (FR-023) — this is what stops a
  metric or anything else undefined from ever reaching a persona, even if a Museum end
  is misbehaving.

A refusal is something a persona may remember, never something to retry blindly or show
a visitor:

```python
from miraveja_studiolink.client import remember_refusal

try:
    await client.publish_comment(
        send_mark=uuid.uuid4(),
        persona=persona,
        text="...",
        verdict=comment_verdict,
        target_comment_id=some_comment_id,
    )
except RefusalReceived as exc:
    remembered = remember_refusal(persona.personaId, exc)
    # exc.reason is neutral by construction (FR-032, Charter 7.2): "conversation_closed"
    # never says a visitor chose to stop interacting, only that this reply didn't land.
```

Looking at the museum (`client.look_at_the_museum`) and fetching a piece's image
(`client.fetch_piece_image`) work the same way and change nothing on the Museum side
(FR-040, FR-040a). Erasure notices (`client.collect_erasure_notices` /
`acknowledge_erasure_notices`) are collected on their own cursor, separate from
experiences, and are never delivered as one (FR-045, FR-046).

## How a Museum end is checked

Build **🏛️ MuseuMusa**'s Studio Link surface against the reference stand-in first — no
Studio, no real persona, nothing but this library:

```bash
uv run miraveja-studiolink standin --port 8080 --script tests/fixtures/one-visitor-comment.yaml
```

That starts a conforming, in-memory Museum end. Point your own Museum end's HTTP client
at it during development the same way a real Studio would, or use it as the target for
the conformance suite while you build the real thing.

Once your own Museum end exists, check it — with no Studio running at all — using the
same suite that is proven (in this library's own test suite) to catch a broken
implementation:

```bash
uv run miraveja-studiolink conformance --target https://your-museum-end.example --credential $TOKEN
```

Each line is one exchange in the contract, reported pass, fail or skip. A `skip` means
the check needs something this suite cannot manufacture against an arbitrary target (an
already-exhibited piece, since candidates only ever reach the human gate, never
exhibition, through this contract) — not a violation. A `fail` is: read the message, fix
the Museum end, run it again. The reference stand-in itself is checked this way in this
library's own CI, and it passes with zero failures.

If you are writing the Museum end in a language other than Python, the conformance
suite is still useful as a specification of exactly what a Studio-side client expects:
every check names the functional requirement (FR-xxx) it is verifying, traceable back to
[`specs/001-studiolink-contract/spec.md`](https://github.com/JomarJunior/miraveja-ecosystem/blob/main/specs/001-studiolink-contract/spec.md)
in the hub.
