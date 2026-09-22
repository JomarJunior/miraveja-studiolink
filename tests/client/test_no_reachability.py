"""No part of the contract names a way to reach the Studio (T036a). FR-001, FR-003."""

from __future__ import annotations

import re

from miraveja_studiolink.contract import load_contract

HUB_DOCUMENT = load_contract()

# Anything that would let the Museum side reach into the Studio: an address, a callback,
# a port, a schedule it could expect the Studio to keep.
FORBIDDEN_NAME_PATTERNS = [
    r"callback",
    r"webhook",
    r"studio(Url|Host|Address|Port|Ip)",
    r"^port$",
    r"^address$",
    r"availabilityWindow",
    r"schedule",
    r"pollUrl",
    r"notifyUrl",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_NAME_PATTERNS]


def _all_strings(obj: object, found: list[str] | None = None) -> list[str]:
    if found is None:
        found = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            found.append(str(key))
            _all_strings(value, found)
    elif isinstance(obj, list):
        for item in obj:
            _all_strings(item, found)
    elif isinstance(obj, str):
        found.append(obj)
    return found


def test_no_schema_property_or_parameter_names_a_way_to_reach_the_studio() -> None:
    names = set()
    for operations in HUB_DOCUMENT["paths"].values():
        for operation in operations.values():
            for param in operation.get("parameters", []):
                names.add(param.get("name", ""))
    for schema in HUB_DOCUMENT["components"]["schemas"].values():
        _collect_property_names(schema, names)

    offenders = [name for name in names if any(p.search(name) for p in _COMPILED)]
    assert not offenders, f"contract names something that could reach the Studio: {offenders}"


def _collect_property_names(node: object, names: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.get("properties", {}).items():
            names.add(key)
            _collect_property_names(value, names)
        if "items" in node:
            _collect_property_names(node["items"], names)
        for key in ("oneOf", "anyOf", "allOf"):
            for variant in node.get(key, []):
                _collect_property_names(variant, names)


def test_the_only_server_variable_names_the_museum_not_the_studio() -> None:
    servers = HUB_DOCUMENT["servers"]
    assert len(servers) == 1
    variables = servers[0].get("variables", {})
    assert set(variables.keys()) == {"museumHost"}


def test_no_operation_is_documented_as_museum_initiated() -> None:
    # A loose textual check: no summary or description anywhere claims the Museum side
    # calls out, pushes, or notifies the Studio.
    suspicious_verbs = re.compile(
        r"\b(push(es)?|notifies?|calls out to|reaches into)\b", re.IGNORECASE
    )
    offenders = [text for text in _all_strings(HUB_DOCUMENT) if suspicious_verbs.search(text)]
    assert not offenders, f"contract text suggests a Museum-initiated call: {offenders}"


def test_every_operation_id_reads_as_studio_initiated() -> None:
    # FR-001: every exchange is started by the Studio. Every operation in this contract
    # is a request the Studio makes (announce, hand over, publish, collect, acknowledge,
    # fetch, look) — none is framed as the Museum delivering to the Studio unprompted.
    operation_ids = [
        operation["operationId"]
        for operations in HUB_DOCUMENT["paths"].values()
        for operation in operations.values()
        if "operationId" in operation
    ]
    assert operation_ids, "expected at least one operation in the contract"
    forbidden_verbs = ("push", "deliver", "notify", "send")
    offenders = [
        op_id
        for op_id in operation_ids
        if any(op_id.lower().startswith(verb) for verb in forbidden_verbs)
    ]
    assert not offenders, f"operation(s) read as Museum-initiated: {offenders}"
