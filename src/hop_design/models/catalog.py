"""Caller-supplied processing catalog and resolved recognition-site contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Span
from hop_design.models.junction import Strand
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import SequenceValidationError, normalize_dna_sequence
from hop_design.models.strand_state import DuplexCut, NickEvent


def _normalize_warning_codes(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(value.strip().upper() for value in values)
    if any(not value for value in normalized):
        raise ValueError("warning_codes must not contain blank values.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("warning_codes must not contain duplicates.")
    return normalized


class SiteOrientation(StrEnum):
    FORWARD = "forward"
    REVERSE = "reverse"


class NickingAgent(HopModel):
    """One strand-specific nicking pattern and cut offset from motif start."""

    agent_id: ReferenceId
    motif_top_5to3: str
    nicked_strand: Strand
    cut_offset: int
    warning_codes: tuple[str, ...]

    @field_validator("motif_top_5to3", mode="before")
    @classmethod
    def normalize_motif(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @field_validator("warning_codes", mode="after")
    @classmethod
    def normalize_warning_codes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_warning_codes(values)


class ReleaseAgent(HopModel):
    """One duplex-release pattern and top/bottom offsets from motif start."""

    agent_id: ReferenceId
    motif_top_5to3: str
    top_cut_offset: int
    bottom_cut_offset: int
    warning_codes: tuple[str, ...]

    @field_validator("motif_top_5to3", mode="before")
    @classmethod
    def normalize_motif(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @field_validator("warning_codes", mode="after")
    @classmethod
    def normalize_warning_codes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_warning_codes(values)


ProcessingAgent = NickingAgent | ReleaseAgent


class ProcessingCatalog(HopModel):
    """A strict versioned set of caller-owned processing entries."""

    schema_id: Literal["hop.processing-catalog/v1"] = Field(
        default="hop.processing-catalog/v1", alias="schema"
    )
    catalog_id: ReferenceId
    nicking_agents: tuple[NickingAgent, ...]
    release_agents: tuple[ReleaseAgent, ...]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> ProcessingCatalog:
        entries: tuple[ProcessingAgent, ...] = self.nicking_agents + self.release_agents
        ids = tuple(entry.agent_id for entry in entries)
        if len(ids) != len(set(ids)):
            raise ValueError("Processing catalog agent ids must be unique across all entry types.")
        if not ids:
            raise ValueError("Processing catalog must contain at least one agent.")
        return self

    def by_id(self, agent_id: str) -> ProcessingAgent:
        """Resolve one entry or fail rather than returning an ambiguous sentinel."""
        entries: tuple[ProcessingAgent, ...] = self.nicking_agents + self.release_agents
        for entry in entries:
            if entry.agent_id == agent_id:
                return entry
        raise KeyError(agent_id)


class ResolvedNickSite(HopModel):
    agent_id: ReferenceId
    site_span: Span
    orientation: SiteOrientation
    matched_sequence: str
    nick: NickEvent


class ResolvedReleaseSite(HopModel):
    agent_id: ReferenceId
    site_span: Span
    orientation: SiteOrientation
    matched_sequence: str
    cut: DuplexCut


class MotifPresence(StrEnum):
    GUARANTEED = "guaranteed"
    POSSIBLE = "possible"
    ABSENT = "absent"


class MotifMatch(HopModel):
    span: Span
    orientation: SiteOrientation
    matched_symbols: str
    certainty: Literal[MotifPresence.GUARANTEED, MotifPresence.POSSIBLE]


class MotifPresenceReport(HopModel):
    status: MotifPresence
    matches: tuple[MotifMatch, ...]

    @model_validator(mode="after")
    def validate_status(self) -> MotifPresenceReport:
        if self.status is MotifPresence.ABSENT and self.matches:
            raise ValueError("An absent motif report cannot contain matches.")
        if self.status is not MotifPresence.ABSENT and not self.matches:
            raise ValueError("A present motif report must contain at least one match.")
        if self.status is MotifPresence.GUARANTEED and not any(
            match.certainty is MotifPresence.GUARANTEED for match in self.matches
        ):
            raise ValueError("Guaranteed status requires at least one guaranteed match.")
        return self


__all__ = [
    "MotifMatch",
    "MotifPresence",
    "MotifPresenceReport",
    "NickingAgent",
    "ProcessingAgent",
    "ProcessingCatalog",
    "ReleaseAgent",
    "ResolvedNickSite",
    "ResolvedReleaseSite",
    "SiteOrientation",
]
