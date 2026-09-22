"""Static review: nothing the Museum side can send names a count, score or amount (T025).

FR-021, FR-038. Walks every successful-response schema in the hub's contract — this is
what a reviewer following User Story 2 acceptance scenario 1 would do by hand, made
repeatable. See test_no_metrics_emitted.py in tests/standin/ for the runtime check.
"""

from __future__ import annotations

import pytest

from miraveja_studiolink.contract import load_contract
from tests.metrics_check import collect_schema_property_names, offending_field_names
from tests.schemas.schema_compare import hub_resolver

HUB_DOCUMENT = load_contract()


def _successful_response_schemas() -> list[tuple[str, str, dict]]:
    schemas = []
    for path, operations in HUB_DOCUMENT["paths"].items():
        for method, operation in operations.items():
            for status, response in operation.get("responses", {}).items():
                if not status.startswith("2"):
                    continue
                for media_type, content in response.get("content", {}).items():
                    if media_type != "application/json":
                        continue
                    schemas.append((f"{method.upper()} {path}", status, content["schema"]))
    return schemas


successful_response_schemas = _successful_response_schemas()
assert successful_response_schemas, "expected at least one JSON success response in the contract"


@pytest.mark.parametrize(
    "operation,status,schema",
    successful_response_schemas,
    ids=[f"{op} {status}" for op, status, _ in successful_response_schemas],
)
def test_no_success_response_carries_a_metric_field(
    operation: str, status: str, schema: dict
) -> None:
    names = collect_schema_property_names(schema, hub_resolver(HUB_DOCUMENT))
    offenders = offending_field_names(names)
    assert not offenders, f"{operation} ({status}) has metric-looking field(s): {offenders}"
