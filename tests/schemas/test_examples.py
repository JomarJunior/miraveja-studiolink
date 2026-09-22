"""Every hub example validates or is refused exactly as intended (FR-035, T007).

`_`-prefixed keys (`_schema`, `_expectedRefusal`, `_why`) are metadata, not part of the
contract, and are stripped before validating (contracts/examples/README.md). This is
also where FR-028 (no tone/conduct judgment), FR-029 (a rejected verdict never crosses)
and FR-042 (no meeting kind from the Museum side) are enforced with no code of their
own: they are just unknown- or malformed-field refusals once the models are closed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from miraveja_studiolink.contract import contract_path
from miraveja_studiolink.messages import SCHEMA_MODELS, classify_validation_error

EXAMPLES_DIR = contract_path().parent / "examples"


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _strip_metadata(data: dict) -> dict:
    return {k: v for k, v in data.items() if not k.startswith("_")}


valid_examples = sorted((EXAMPLES_DIR / "valid").glob("*.json"))
invalid_examples = sorted((EXAMPLES_DIR / "invalid").glob("*.json"))

assert valid_examples, "expected at least one valid example fixture in the hub"
assert invalid_examples, "expected at least one invalid example fixture in the hub"


@pytest.mark.parametrize("path", valid_examples, ids=lambda p: p.name)
def test_valid_example_validates(path: Path) -> None:
    data = _load(path)
    model = SCHEMA_MODELS[data["_schema"]]
    model.model_validate(_strip_metadata(data))


@pytest.mark.parametrize("path", invalid_examples, ids=lambda p: p.name)
def test_invalid_example_is_refused_for_the_expected_reason(path: Path) -> None:
    data = _load(path)
    model = SCHEMA_MODELS[data["_schema"]]
    expected_reason = data["_expectedRefusal"]

    with pytest.raises(ValidationError) as excinfo:
        model.model_validate(_strip_metadata(data))

    assert classify_validation_error(excinfo.value) == expected_reason


def test_every_example_is_covered_by_a_known_schema() -> None:
    for path in [*valid_examples, *invalid_examples]:
        data = _load(path)
        assert data["_schema"] in SCHEMA_MODELS, f"{path.name} names an unknown schema"
