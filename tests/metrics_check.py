"""Shared denylist for anything that smells like a metric or monetary value (FR-021).

Used both to review the hub's contract as written (T025, static) and to check the
stand-in's actual runtime output (T026, behavioral) — the same vocabulary either way,
since a field that would be a problem in the schema is a problem in the wire response
too. Scans property *names* only, never free-text descriptions or enum values, so a
description that explains the rule ("carries no score") is never mistaken for breaking it.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

FORBIDDEN_NAME_PATTERNS = [
    r"count",
    r"total",
    r"score",
    r"rank",
    r"rating",
    r"popular",
    r"trend",
    r"impression",
    r"amount",
    r"price",
    r"pay",
    r"revenue",
    r"money",
    r"currency",
    r"tally",
    r"percent",
    r"ratio",
    r"follower",
    r"subscriber",
    r"vote",
    r"upvote",
    r"downvote",
    r"star",
    r"views?$",
    r"num[A-Z]",
]

_COMPILED = [re.compile(pattern, re.IGNORECASE) for pattern in FORBIDDEN_NAME_PATTERNS]


def offending_field_names(names: set[str]) -> list[str]:
    return sorted(name for name in names if any(p.search(name) for p in _COMPILED))


def collect_object_keys(obj: Any, keys: set[str] | None = None) -> set[str]:
    """Every dict key reachable anywhere within `obj` (a JSON Schema doc, or JSON data)."""
    if keys is None:
        keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            collect_object_keys(value, keys)
    elif isinstance(obj, list):
        for item in obj:
            collect_object_keys(item, keys)
    return keys


def collect_schema_property_names(
    schema: dict[str, Any],
    resolver: Callable[[str], dict[str, Any]],
    *,
    names: set[str] | None = None,
    seen_refs: set[str] | None = None,
) -> set[str]:
    """Every property name reachable from `schema`, resolving `$ref` as it goes."""
    if names is None:
        names = set()
    if seen_refs is None:
        seen_refs = set()

    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in seen_refs:
            return names
        seen_refs.add(ref)
        schema = resolver(ref)

    for key in ("properties",):
        for name, sub in schema.get(key, {}).items():
            names.add(name)
            collect_schema_property_names(sub, resolver, names=names, seen_refs=seen_refs)

    if "items" in schema:
        collect_schema_property_names(schema["items"], resolver, names=names, seen_refs=seen_refs)

    for key in ("oneOf", "anyOf", "allOf"):
        for variant in schema.get(key, []):
            collect_schema_property_names(variant, resolver, names=names, seen_refs=seen_refs)

    return names
