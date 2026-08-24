"""Strict contracts for exact precursors from one released-foldback geometry."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from itertools import islice
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.discovery.released_foldback import ReleasedFoldbackGeometryHit
from hop_design.models.sequence import SequenceValidationError, normalize_dna_sequence
from hop_design.serialization import sha256_digest

ReleasedFoldbackPrecursorSearchStatus = Literal["complete", "infeasible", "truncated"]
ReleasedFoldbackPrecursorSearchTruncation = Literal["max_search_nodes", "max_hits"]


class ReleasedFoldbackPrecursorBlocker(StrEnum):
    """Reason a caller template admits no sequence for the selected geometry."""

    CALLER_DOMAIN_CONFLICT = "caller_domain_conflict"


class ReleasedFoldbackPrecursorSearchRequest(HopModel):
    """One selected geometry and the exact IUPAC domain a caller authorizes."""

    schema_id: Literal["hop.released-foldback-precursor-search-request/v1"] = Field(
        default="hop.released-foldback-precursor-search-request/v1",
        alias="schema",
    )
    geometry: ReleasedFoldbackGeometryHit
    precursor_template: str

    @field_validator("precursor_template", mode="before")
    @classmethod
    def normalize_precursor_template(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @model_validator(mode="after")
    def validate_template_extent(self) -> ReleasedFoldbackPrecursorSearchRequest:
        if len(self.precursor_template) != self.geometry.required_precursor.value:
            raise ValueError("precursor_template length must equal geometry.required_precursor.")
        return self


class ReleasedFoldbackPrecursorSearchLimits(HopModel):
    """Hard budgets for exact precursor enumeration and returned hits."""

    max_search_nodes: int = Field(ge=1)
    max_hits: int = Field(ge=1)


def released_foldback_precursor_candidate_id(*, geometry_id: str, sequence: str) -> str:
    """Return content identity for one exact precursor and selected geometry."""
    content = (
        json.dumps(
            {"geometry_id": geometry_id, "precursor_sequence": sequence},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    return f"hop:released-foldback-precursor/{hashlib.sha256(content).hexdigest()}@1"


class ReleasedFoldbackPrecursorCandidate(HopModel):
    """One exact precursor inside a selected released-foldback geometry."""

    candidate_id: str = Field(pattern=r"^hop:released-foldback-precursor/[0-9a-f]{64}@1$")
    canonical_ordinal: int = Field(ge=1)
    geometry_id: str = Field(pattern=r"^hop:released-foldback-geometry/[0-9a-f]{64}@1$")
    precursor_sequence: str
    precursor_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("precursor_sequence", mode="before")
    @classmethod
    def normalize_precursor_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_identity(self) -> ReleasedFoldbackPrecursorCandidate:
        expected_digest = sha256_digest(self.precursor_sequence.encode("utf-8"))
        if self.precursor_digest != expected_digest:
            raise ValueError("precursor_digest must match precursor_sequence.")
        expected_id = released_foldback_precursor_candidate_id(
            geometry_id=self.geometry_id,
            sequence=self.precursor_sequence,
        )
        if self.candidate_id != expected_id:
            raise ValueError("candidate_id must match the geometry and precursor sequence.")
        return self


class ReleasedFoldbackPrecursorSearchResult(HopModel):
    """Bounded exact-sequence materialization for one selected geometry."""

    schema_id: Literal["hop.released-foldback-precursor-search-result/v1"] = Field(
        default="hop.released-foldback-precursor-search-result/v1",
        alias="schema",
    )
    status: ReleasedFoldbackPrecursorSearchStatus
    request: ReleasedFoldbackPrecursorSearchRequest
    limits: ReleasedFoldbackPrecursorSearchLimits
    hits: tuple[ReleasedFoldbackPrecursorCandidate, ...]
    candidate_space_size: int = Field(ge=0)
    search_nodes_examined: int = Field(ge=0)
    observed_hit_count: int = Field(ge=0)
    blockers: tuple[ReleasedFoldbackPrecursorBlocker, ...] = ()
    truncated_by: tuple[ReleasedFoldbackPrecursorSearchTruncation, ...] = ()

    @model_validator(mode="after")
    def validate_search(self) -> ReleasedFoldbackPrecursorSearchResult:
        from hop_design.models.discovery.released_foldback_candidate_evaluation import (
            enumerate_released_foldback_precursors,
            released_foldback_precursor_candidate_count,
            released_foldback_precursor_domains,
        )

        domains = released_foldback_precursor_domains(self.request)
        expected_space = (
            0
            if domains is None
            else released_foldback_precursor_candidate_count(self.request, domains=domains)
        )
        if self.candidate_space_size != expected_space:
            raise ValueError("candidate_space_size must derive from intersected domains.")
        expected_examined = min(expected_space, self.limits.max_search_nodes)
        if self.search_nodes_examined != expected_examined:
            raise ValueError("search_nodes_examined must exhaust the available node budget.")
        if self.observed_hit_count != expected_examined:
            raise ValueError("Every examined exact precursor must be an observed hit.")

        sequences = (
            ()
            if domains is None
            else tuple(
                islice(
                    enumerate_released_foldback_precursors(self.request, domains=domains),
                    expected_examined,
                )
            )
        )
        returned_sequences = sequences[: self.limits.max_hits]
        if len(self.hits) != len(returned_sequences):
            raise ValueError("Returned hits must exhaust the available hit budget.")
        expected_ordinals = tuple(range(1, len(self.hits) + 1))
        if tuple(candidate.canonical_ordinal for candidate in self.hits) != expected_ordinals:
            raise ValueError("Returned candidate ordinals must be contiguous and one-based.")
        for candidate, sequence in zip(self.hits, returned_sequences, strict=True):
            if candidate.geometry_id != self.request.geometry.candidate_id:
                raise ValueError("Candidate geometry_id must equal the selected geometry.")
            if candidate.precursor_sequence != sequence:
                raise ValueError("Returned candidates must use canonical physical order.")

        expected_blockers = (
            (ReleasedFoldbackPrecursorBlocker.CALLER_DOMAIN_CONFLICT,)
            if expected_space == 0
            else ()
        )
        if self.blockers != expected_blockers:
            raise ValueError("blockers must exactly describe caller-domain infeasibility.")
        expected_truncation: list[ReleasedFoldbackPrecursorSearchTruncation] = []
        if expected_examined < expected_space:
            expected_truncation.append("max_search_nodes")
        if len(returned_sequences) < expected_examined:
            expected_truncation.append("max_hits")
        if self.truncated_by != tuple(expected_truncation):
            raise ValueError("truncated_by must exactly describe node and hit truncation.")
        if (self.status == "truncated") != bool(self.truncated_by):
            raise ValueError("Truncated status and truncation evidence must agree.")
        if self.status == "infeasible" and (expected_space or self.hits):
            raise ValueError("An infeasible search must have an empty candidate space.")
        if self.status == "complete":
            if expected_space == 0 or expected_examined != expected_space:
                raise ValueError("A complete search must exhaust a nonempty candidate space.")
            if len(self.hits) != expected_space:
                raise ValueError("A complete search must return every exact precursor.")
        return self


__all__ = [
    "ReleasedFoldbackPrecursorBlocker",
    "ReleasedFoldbackPrecursorCandidate",
    "ReleasedFoldbackPrecursorSearchLimits",
    "ReleasedFoldbackPrecursorSearchRequest",
    "ReleasedFoldbackPrecursorSearchResult",
]
