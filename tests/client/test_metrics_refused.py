"""Every contaminated message from the Museum side is refused in full (T023).

FR-021 to FR-023, User Story 2 acceptance scenario 2.
"""

from __future__ import annotations

import json

import pytest

from miraveja_studiolink.contract import contract_path
from miraveja_studiolink.messages.refusal import RefusalReceived

EXAMPLES_DIR = contract_path().parent / "examples" / "invalid"

# Every invalid example whose schema flows from the Museum toward the Studio: these are
# the ones a Studio end can actually receive over the wire and must refuse outright.
CONTAMINATED_EXAMPLES = [
    "experience-batch-with-count.json",
    "experience-meeting-kind.json",
]


def _strip_metadata(data: dict) -> dict:
    return {k: v for k, v in data.items() if not k.startswith("_")}


@pytest.mark.asyncio
@pytest.mark.parametrize("filename", CONTAMINATED_EXAMPLES)
async def test_a_contaminated_experience_batch_is_refused_in_full(
    client, state, persona, filename: str
) -> None:
    data = json.loads((EXAMPLES_DIR / filename).read_text(encoding="utf-8"))
    state.register_persona(persona.personaId, persona.publicName)
    state.force_response("collectExperiences", _strip_metadata(data))

    with pytest.raises(RefusalReceived) as excinfo:
        await client.collect_experiences(persona.personaId)

    assert excinfo.value.reason == "unknown_field"


@pytest.mark.asyncio
async def test_nothing_from_a_refused_message_reaches_the_persona(client, state, persona) -> None:
    data = json.loads(
        (EXAMPLES_DIR / "experience-batch-with-count.json").read_text(encoding="utf-8")
    )
    state.register_persona(persona.personaId, persona.publicName)
    state.force_response("collectExperiences", _strip_metadata(data))

    caught = None
    try:
        await client.collect_experiences(persona.personaId)
    except RefusalReceived as exc:
        caught = exc

    assert caught is not None
    # The only thing the caller gets is the refusal itself, never a partial batch.
    assert not hasattr(caught, "items")
