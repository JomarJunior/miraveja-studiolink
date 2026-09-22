"""Pydantic v2 models for every Studio Link message, checked against the hub's schemas.

Every model here is closed (`additionalProperties: false`, FR-023): an unknown field
raises `pydantic.ValidationError`, which `classify_validation_error` turns into the
Refusal reason a conforming Museum end must answer with (R-10).
"""

from __future__ import annotations

from miraveja_studiolink.messages.candidates import Candidate, CandidateAccepted, Label
from miraveja_studiolink.messages.classify import classify_validation_error
from miraveja_studiolink.messages.comments import (
    CommentIdTarget,
    CommentPublished,
    CommentTarget,
    PersonaComment,
    PieceTarget,
)
from miraveja_studiolink.messages.common import Acknowledgement, PersonaRef, Verdict, VisitorRef
from miraveja_studiolink.messages.erasure import ErasureNotice, ErasureNoticeBatch
from miraveja_studiolink.messages.exhibition import (
    ConversationEntry,
    ExhibitedPiece,
    ExhibitionView,
)
from miraveja_studiolink.messages.experiences import (
    CommentExperience,
    Experience,
    ExperienceBatch,
    GateOutcomeExperience,
    ReactionExperience,
)
from miraveja_studiolink.messages.presence import PresenceAnnouncement, PresenceState
from miraveja_studiolink.messages.refusal import Refusal, RefusalReason, RefusalReceived

__all__ = [
    "Acknowledgement",
    "Candidate",
    "CandidateAccepted",
    "CommentExperience",
    "CommentIdTarget",
    "CommentPublished",
    "CommentTarget",
    "ConversationEntry",
    "ErasureNotice",
    "ErasureNoticeBatch",
    "ExhibitedPiece",
    "ExhibitionView",
    "Experience",
    "ExperienceBatch",
    "GateOutcomeExperience",
    "Label",
    "PersonaComment",
    "PersonaRef",
    "PieceTarget",
    "PresenceAnnouncement",
    "PresenceState",
    "ReactionExperience",
    "Refusal",
    "RefusalReason",
    "RefusalReceived",
    "Verdict",
    "VisitorRef",
    "classify_validation_error",
]

# Maps each schema name in the hub's contract to the model that represents it.
SCHEMA_MODELS: dict[str, type] = {
    "PersonaRef": PersonaRef,
    "VisitorRef": VisitorRef,
    "Verdict": Verdict,
    "Acknowledgement": Acknowledgement,
    "PresenceAnnouncement": PresenceAnnouncement,
    "Candidate": Candidate,
    "PersonaComment": PersonaComment,
    "ExperienceBatch": ExperienceBatch,
    "CommentExperience": CommentExperience,
    "ReactionExperience": ReactionExperience,
    "GateOutcomeExperience": GateOutcomeExperience,
    "ErasureNoticeBatch": ErasureNoticeBatch,
    "ExhibitionView": ExhibitionView,
    "Refusal": Refusal,
}
