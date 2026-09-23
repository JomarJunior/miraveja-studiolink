"""Pin the free-text surface flowing toward the Studio (FR-021).

FR-021 forbids a metric embedded *in another field*, not only a metric with a field of
its own. A schema can stop `reactionCount`; it cannot stop a Museum end writing "you got
412 likes this week" inside a free-text `reason`. Nothing can fully enforce that, so this
test does the next best thing: it pins the exact set of free-form strings a persona can
ever read, so adding another one is a deliberate act with this rule in front of you.

Every field listed below is authored by a human or a persona, never composed by the
Museum side, which keeps the risk at "a Museum end could misbehave" rather than "the
contract does it for you". See docs/usage.md, "Free text is the one surface schemas
cannot police".
"""

from __future__ import annotations

from typing import Any

from miraveja_studiolink.contract import load_contract
from tests.schemas.schema_compare import hub_resolver

HUB_DOCUMENT = load_contract()

# Free-form strings a persona can read, and who writes each one.
ALLOWED_FREE_TEXT = {
    "text",  # a visitor's or another persona's own words
    "reason",  # the human gate's words, addressed to the persona
    "detail",  # a refusal detail, for the team's logs, never shown to a persona
    "title",  # written by the persona who made the piece
    "statement",  # the persona's own voice
    "neutralDescription",  # DescriDiva's neutral description
    "publicName",  # a persona's public name
    "displayName",  # a visitor's chosen public name
}

# A string carrying any of these is shaped, not prose: it cannot hold a sentence.
_STRUCTURED = ("enum", "const", "format", "pattern")


def _free_text_field_names(node: Any, resolve: Any, seen: set[int] | None = None) -> set[str]:
    seen = seen if seen is not None else set()
    if not isinstance(node, dict) or id(node) in seen:
        return set()
    seen.add(id(node))
    if "$ref" in node:
        return _free_text_field_names(resolve(node["$ref"]), resolve, seen)

    found: set[str] = set()
    for name, prop in node.get("properties", {}).items():
        target = resolve(prop["$ref"]) if isinstance(prop, dict) and "$ref" in prop else prop
        if isinstance(target, dict):
            type_ = target.get("type")
            is_string = type_ == "string" or (isinstance(type_, list) and "string" in type_)
            if is_string and not any(key in target for key in _STRUCTURED):
                found.add(name)
            found |= _free_text_field_names(target, resolve, seen)
    for key in ("items", "additionalProperties"):
        found |= _free_text_field_names(node.get(key), resolve, seen)
    for key in ("oneOf", "anyOf", "allOf"):
        for variant in node.get(key, []):
            found |= _free_text_field_names(variant, resolve, seen)
    return found


def _success_response_schemas() -> list[tuple[str, dict]]:
    """Every JSON response the Studio can read, refusals included.

    Refusals are reached through `$ref` into components/responses, so they are resolved
    here rather than skipped — `detail` is free text a persona could be shown by mistake.
    """
    resolve = hub_resolver(HUB_DOCUMENT)
    schemas = []
    for path, operations in HUB_DOCUMENT["paths"].items():
        for method, operation in operations.items():
            for status, response in operation.get("responses", {}).items():
                if "$ref" in response:
                    response = resolve(response["$ref"])
                for media_type, content in response.get("content", {}).items():
                    if media_type != "application/json":
                        continue
                    schemas.append((f"{method.upper()} {path} ({status})", content["schema"]))
    return schemas


def test_only_known_free_text_reaches_the_studio() -> None:
    resolve = hub_resolver(HUB_DOCUMENT)
    unexpected: dict[str, set[str]] = {}
    for operation, schema in _success_response_schemas():
        extra = _free_text_field_names(schema, resolve) - ALLOWED_FREE_TEXT
        if extra:
            unexpected[operation] = extra
    assert not unexpected, (
        f"new free-text field(s) reaching the Studio: {unexpected}. Free text is the one "
        "place a metric can hide that no schema catches (FR-021). Add it to "
        "ALLOWED_FREE_TEXT only once you are sure a human or a persona writes it, never "
        "the Museum side."
    )


def test_the_allowlist_has_no_dead_entries() -> None:
    resolve = hub_resolver(HUB_DOCUMENT)
    present: set[str] = set()
    for _, schema in _success_response_schemas():
        present |= _free_text_field_names(schema, resolve)
    dead = ALLOWED_FREE_TEXT - present
    assert not dead, f"ALLOWED_FREE_TEXT lists field(s) the contract no longer has: {sorted(dead)}"
