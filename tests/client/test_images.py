"""An image is fetched by piece identifier through the contract (T019a). FR-040a, R-14."""

from __future__ import annotations

import uuid

import pytest

from miraveja_studiolink.messages.refusal import RefusalReceived
from tests.helpers import TINY_PNG, accepted_verdict


@pytest.mark.asyncio
async def test_an_exhibited_pieces_image_is_fetched_by_piece_id(client, state, persona) -> None:
    piece_id = uuid.uuid4()
    await state.seed_exhibited_piece(
        piece_id=piece_id,
        persona_id=persona.personaId,
        public_name=persona.publicName,
        title="t",
        statement="s",
        neutral_description="d",
        image_bytes=TINY_PNG,
        image_media_type="image/png",
    )

    image_bytes, media_type = await client.fetch_piece_image(piece_id)

    assert image_bytes == TINY_PNG
    assert media_type == "image/png"


@pytest.mark.asyncio
async def test_the_image_of_a_candidate_just_handed_over_is_fetchable(client, persona) -> None:
    piece_id = uuid.uuid4()
    await client.hand_over_candidate(
        send_mark=uuid.uuid4(),
        persona=persona,
        piece_id=piece_id,
        title="t",
        statement="s",
        neutral_description="d",
        labels=[],
        verdict=accepted_verdict(),
        image_bytes=TINY_PNG,
        image_media_type="image/png",
    )

    image_bytes, media_type = await client.fetch_piece_image(piece_id)
    assert image_bytes == TINY_PNG


@pytest.mark.asyncio
async def test_fetching_an_unknown_pieces_image_is_refused(client) -> None:
    with pytest.raises(RefusalReceived) as excinfo:
        await client.fetch_piece_image(uuid.uuid4())
    assert excinfo.value.reason == "piece_not_on_display"


@pytest.mark.asyncio
async def test_the_exhibition_view_names_no_location_outside_the_contract(
    client, state, persona
) -> None:
    piece_id = uuid.uuid4()
    await state.seed_exhibited_piece(
        piece_id=piece_id,
        persona_id=persona.personaId,
        public_name=persona.publicName,
        title="t",
        statement="s",
        neutral_description="d",
    )

    view = await client.look_at_the_museum(persona.personaId)

    piece = view.pieces[0]
    dumped = piece.model_dump()
    assert "imageMediaType" in dumped
    assert not any("url" in key.lower() for key in dumped)
