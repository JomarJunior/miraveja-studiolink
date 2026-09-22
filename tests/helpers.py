"""Small builders shared across the test suite. Every name here is synthetic (SC-008)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from miraveja_studiolink.messages.common import PersonaRef, Verdict, VerdictScope

TINY_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def synthetic_persona(name: str = "Synthetic Persona One") -> PersonaRef:
    return PersonaRef(personaId=uuid.uuid4(), publicName=name)


def accepted_verdict(
    scope: VerdictScope = "charter_and_quality", reason: str = "Within the Charter."
) -> Verdict:
    return Verdict(outcome="accepted", reason=reason, decidedAt=datetime.now(UTC), scope=scope)
