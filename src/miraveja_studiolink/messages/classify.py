"""Turns a Pydantic ValidationError into the Refusal reason it deserves.

Both ends use this: the stand-in, to answer a bad request the same way any conforming
Museum end must (R-10); the client, to classify a Museum response it refuses to trust
(FR-023). Keeping one function means both sides read the same message the same way.
"""

from __future__ import annotations

from pydantic import ValidationError

from miraveja_studiolink.messages.refusal import RefusalReason

_UNION_TAG_ERROR_TYPES = {"union_tag_invalid", "union_tag_not_found"}


def classify_validation_error(exc: ValidationError) -> RefusalReason:
    errors = exc.errors()

    if any(e["type"] == "extra_forbidden" for e in errors):
        return "unknown_field"
    if any(e["type"] in _UNION_TAG_ERROR_TYPES for e in errors):
        return "unknown_field"

    for e in errors:
        if e["loc"] == ("verdict",) and e["type"] == "missing":
            return "missing_verdict"
        if e["loc"][-2:] == ("verdict", "outcome") and e["type"] == "literal_error":
            return "rejected_verdict"

    for e in errors:
        if "labels" in e["loc"] and e["type"] == "literal_error":
            return "unknown_label"

    return "malformed"
