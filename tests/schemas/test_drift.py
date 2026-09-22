"""The models' generated schemas match the hub's studiolink-v1.yaml (R-13, T009).

Fails when either side changes alone: edit a Pydantic model without updating the hub
schema, or the reverse, and one of these assertions breaks.
"""

from __future__ import annotations

import pytest
from schema_compare import diff

from miraveja_studiolink.contract import load_contract
from miraveja_studiolink.messages import SCHEMA_MODELS

HUB_DOCUMENT = load_contract()


@pytest.mark.parametrize("schema_name", sorted(SCHEMA_MODELS), ids=lambda n: n)
def test_model_matches_hub_schema(schema_name: str) -> None:
    hub_schema = HUB_DOCUMENT["components"]["schemas"][schema_name]
    model = SCHEMA_MODELS[schema_name]

    hub_side, model_side = diff(hub_schema, HUB_DOCUMENT, model)

    assert hub_side == model_side, (
        f"{schema_name} has drifted from the hub's studiolink-v1.yaml.\n"
        f"hub:   {hub_side}\nmodel: {model_side}"
    )


def test_every_hub_message_schema_has_a_model() -> None:
    # Response-only inline schemas (CandidateAccepted, CommentPublished, the versions
    # response) are not named top-level schemas in the hub document, so they are not
    # expected here.
    hub_schema_names = set(HUB_DOCUMENT["components"]["schemas"])
    missing = hub_schema_names - set(SCHEMA_MODELS) - {"Experience"}
    assert not missing, f"no Pydantic model registered for hub schemas: {missing}"
