"""The shared base every Studio Link message model builds on.

Every schema in the contract is closed (`additionalProperties: false`): an unknown field
is a refusal, not an ignored extra (FR-023). `ClosedModel` makes that the default for
every message in both directions so no model can forget it.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
