"""Strict parsing of Museum responses: an unknown field refuses the whole message (FR-023)."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from miraveja_studiolink.messages.classify import classify_validation_error
from miraveja_studiolink.messages.refusal import RefusalReceived


def parse_strict[ModelT: BaseModel](model: type[ModelT], data: object) -> ModelT:
    """Parse `data` as `model`, or raise `RefusalReceived` for the Studio to act on.

    Nothing from a message that fails this parse reaches a persona (FR-023): the caller
    gets an exception, never a partially-populated model.
    """
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        reason = classify_validation_error(exc)
        raise RefusalReceived(reason, detail=str(exc)) from exc
