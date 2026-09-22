"""Structural JSON Schema comparison for the drift test (T009, R-13).

Compares two JSON Schemas for the same meaning while tolerating the stylistic
differences between hand-written OpenAPI/JSON Schema and Pydantic v2's generated
schema: `$ref` vs. inlined definitions, `type: [X, "null"]` vs. `anyOf` nullable, and
member ordering in `oneOf`/`anyOf`. It still catches what matters: a changed type, a
changed required set, a changed enum or const, changed length/range bounds, and
whether extra properties are allowed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Resolver = Callable[[str], dict[str, Any]]

_CONSTRAINT_KEYS = (
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "minItems",
    "maxItems",
    "uniqueItems",
    "format",
)


def _resolve(node: dict[str, Any], resolver: Resolver) -> dict[str, Any]:
    if "$ref" in node:
        return resolver(node["$ref"])
    return node


def _infer_type(value: Any) -> str | None:
    # bool before int: bool is an int subclass in Python.
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return None


def normalize(node: dict[str, Any], resolver: Resolver) -> Any:
    node = _resolve(node, resolver)

    if "anyOf" in node or "oneOf" in node:
        key = "anyOf" if "anyOf" in node else "oneOf"
        variants = [_resolve(v, resolver) for v in node[key]]
        non_null = [v for v in variants if v.get("type") != "null"]
        has_null = any(v.get("type") == "null" for v in variants)
        if has_null and len(non_null) == 1:
            merged = dict(non_null[0])
            result = normalize(merged, resolver)
            if isinstance(result, dict):
                result = dict(result)
                result["nullable"] = True
            return result
        return {"oneOf": sorted((normalize(v, resolver) for v in variants), key=repr)}

    type_ = node.get("type")
    nullable = False
    if isinstance(type_, list):
        types = set(type_)
        if "null" in types:
            nullable = True
            types.discard("null")
        type_ = sorted(types)[0] if len(types) == 1 else sorted(types)

    if type_ is None:
        # A bare const/enum with no explicit "type" implies one from its values
        # (hand-written schemas in the hub tend to omit the redundant type keyword).
        if "const" in node:
            type_ = _infer_type(node["const"])
        elif "enum" in node and node["enum"]:
            type_ = _infer_type(node["enum"][0])

    result: dict[str, Any] = {}
    if type_ is not None:
        result["type"] = type_
    if nullable:
        result["nullable"] = True
    if "const" in node:
        result["const"] = node["const"]
    if "enum" in node:
        result["enum"] = sorted(node["enum"])
    for key in _CONSTRAINT_KEYS:
        if key in node:
            result[key] = node[key]

    if type_ == "object" or "properties" in node:
        required = set(node.get("required", []))
        result["additionalProperties"] = node.get("additionalProperties", True)
        result["required"] = sorted(required)
        props = {}
        for name, sub in node.get("properties", {}).items():
            normalized = normalize(sub, resolver)
            if name not in required and isinstance(normalized, dict):
                normalized = {k: v for k, v in normalized.items() if k != "nullable"}
            props[name] = normalized
        result["properties"] = props

    if type_ == "array" or "items" in node:
        items = node.get("items")
        if items is not None:
            result["items"] = normalize(items, resolver)

    return result


def hub_resolver(document: dict[str, Any]) -> Resolver:
    def resolve(ref: str) -> dict[str, Any]:
        assert ref.startswith("#/"), f"unsupported external $ref: {ref}"
        node: Any = document
        for part in ref[2:].split("/"):
            node = node[part]
        return node

    return resolve


def pydantic_resolver(schema: dict[str, Any]) -> Resolver:
    defs = schema.get("$defs", {})

    def resolve(ref: str) -> dict[str, Any]:
        assert ref.startswith("#/$defs/"), f"unexpected $ref shape: {ref}"
        return defs[ref[len("#/$defs/") :]]

    return resolve


def diff(hub_schema: dict[str, Any], hub_doc: dict[str, Any], model: type) -> tuple[Any, Any]:
    """Normalized (hub, model) schema pair for one message, ready to assert equal."""
    pydantic_schema = model.model_json_schema()
    hub_side = normalize(hub_schema, hub_resolver(hub_doc))
    model_side = normalize(pydantic_schema, pydantic_resolver(pydantic_schema))
    return hub_side, model_side
