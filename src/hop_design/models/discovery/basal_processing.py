"""Strict contracts for terminal basal processing geometry discovery."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from math import prod
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.catalog import SiteOrientation
from hop_design.models.junction import Strand
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import SequenceValidationError, iupac_bases, normalize_dna_sequence

PostNickDomainMode = Literal["compatible", "preserve"]
BasalProcessingGeometryStatus = Literal["complete", "infeasible", "truncated"]
BasalProcessingGeometryTruncation = Literal["max_search_nodes", "max_hits"]


class BasalProcessingGeometryBlocker(StrEnum):
    """Physical reasons why one exact terminal-nick geometry is unusable."""

    RELEASE_NICK_DOMAIN_CONFLICT = "release_nick_domain_conflict"
    RETAINED_SCAR_DOMAIN_EMPTY = "retained_scar_domain_empty"
    POST_NICK_DOMAIN_CONFLICT = "post_nick_domain_conflict"
    POST_NICK_DOMAIN_UNCOVERED = "post_nick_domain_uncovered"
    POST_NICK_DOMAIN_NARROWED = "post_nick_domain_narrowed"


_BLOCKER_ORDER = {blocker: index for index, blocker in enumerate(BasalProcessingGeometryBlocker)}


class RelativeBaseDomain(HopModel):
    """Allowed exact bases at one signed coordinate relative to the release top cut."""

    relative_coordinate: int
    allowed_bases: tuple[Literal["A", "C", "G", "T"], ...]

    @field_validator("allowed_bases", mode="before")
    @classmethod
    def normalize_allowed_bases(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def validate_allowed_bases(self) -> RelativeBaseDomain:
        if tuple(sorted(set(self.allowed_bases))) != self.allowed_bases:
            raise ValueError("allowed_bases must be unique and use canonical lexical order.")
        return self


class BasalProcessingGeometryRequest(HopModel):
    """Caller-declared release, terminal nick, scar, and post-nick domains."""

    schema_id: Literal["hop.basal-processing-geometry-request/v1"] = Field(
        default="hop.basal-processing-geometry-request/v1",
        alias="schema",
    )
    release_agent_id: ReferenceId
    release_orientation: SiteOrientation
    terminal_nicked_strand: Strand
    retained_scar_template: str
    post_nick_template: str
    post_nick_domain_mode: PostNickDomainMode
    require_release_site_excised: bool

    @field_validator("retained_scar_template", mode="before")
    @classmethod
    def normalize_retained_scar_template(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        normalized = normalize_dna_sequence(value, allow_degenerate=True)
        if len(normalized) != 4:
            raise ValueError("Basal processing requires a four nucleotides retained scar template.")
        return normalized

    @field_validator("post_nick_template", mode="before")
    @classmethod
    def normalize_post_nick_template(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)


class BasalReleaseGeometry(HopModel):
    """One release site normalized to a signed top-cut coordinate origin."""

    release_agent_id: ReferenceId
    orientation: SiteOrientation
    oriented_motif_top_5to3: str
    site_start: int
    site_end: int
    top_cut: Literal[0] = 0
    bottom_cut: int
    recognition_site_excised: bool

    @field_validator("oriented_motif_top_5to3", mode="before")
    @classmethod
    def normalize_motif(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @model_validator(mode="after")
    def validate_geometry(self) -> BasalReleaseGeometry:
        if self.site_end - self.site_start != len(self.oriented_motif_top_5to3):
            raise ValueError("Release site extent must equal its oriented motif length.")
        if self.bottom_cut != 4:
            raise ValueError("Basal release geometry must produce a four-nucleotide retained scar.")
        expected_excised = self.site_end <= self.top_cut or self.site_start >= self.bottom_cut
        if self.recognition_site_excised is not expected_excised:
            raise ValueError(
                "Release recognition-site disposition must derive from its signed span."
            )
        return self


class BasalProcessingGeometryFeasibility(HopModel):
    """Complete geometry audit for one nicking agent at the exact terminal boundary."""

    release_agent_id: ReferenceId
    nicking_agent_id: ReferenceId
    orientation: SiteOrientation
    oriented_motif_top_5to3: str
    nick_site_start: int
    nick_site_end: int
    nick_boundary: int
    nicked_strand: Strand
    resolved_domains: tuple[RelativeBaseDomain, ...]
    retained_scar_domains: tuple[RelativeBaseDomain, ...]
    post_nick_domains: tuple[RelativeBaseDomain, ...]
    feasible_scar_count: int = Field(ge=0)
    blockers: tuple[BasalProcessingGeometryBlocker, ...]
    compatible: bool

    @field_validator("oriented_motif_top_5to3", mode="before")
    @classmethod
    def normalize_motif(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @model_validator(mode="after")
    def validate_geometry(self) -> BasalProcessingGeometryFeasibility:
        if self.nick_site_end - self.nick_site_start != len(self.oriented_motif_top_5to3):
            raise ValueError("Nick site extent must equal its oriented motif length.")
        if self.nick_boundary != 4:
            raise ValueError(
                "Basal terminal nick boundary must follow the four-base retained scar."
            )
        expected_retained_coordinates = tuple(range(4))
        if tuple(domain.relative_coordinate for domain in self.retained_scar_domains) != (
            expected_retained_coordinates
        ):
            raise ValueError("Retained scar domains must cover signed coordinates 0 through 3.")
        if tuple(domain.relative_coordinate for domain in self.resolved_domains) != tuple(
            sorted(domain.relative_coordinate for domain in self.resolved_domains)
        ):
            raise ValueError("Resolved domains must use signed coordinate order.")
        if len({domain.relative_coordinate for domain in self.resolved_domains}) != len(
            self.resolved_domains
        ):
            raise ValueError("Resolved domains must contain unique signed coordinates.")
        expected_count = prod(len(domain.allowed_bases) for domain in self.retained_scar_domains)
        if self.feasible_scar_count != expected_count:
            raise ValueError("feasible_scar_count must derive from retained scar domains.")
        if len(set(self.blockers)) != len(self.blockers):
            raise ValueError("Geometry blockers must not contain duplicates.")
        if self.blockers != tuple(sorted(self.blockers, key=_BLOCKER_ORDER.__getitem__)):
            raise ValueError("Geometry blockers must use canonical order.")
        if self.compatible is bool(self.blockers):
            raise ValueError("compatible must be true exactly when blockers are empty.")
        empty_scar = any(not domain.allowed_bases for domain in self.retained_scar_domains)
        if empty_scar != (
            BasalProcessingGeometryBlocker.RETAINED_SCAR_DOMAIN_EMPTY in self.blockers
        ):
            raise ValueError("Retained scar emptiness and its blocker must agree.")
        return self


def basal_processing_geometry_id(row: BasalProcessingGeometryFeasibility) -> str:
    """Return content identity for one compatible physical geometry."""
    payload = row.model_dump(mode="json", by_alias=True)
    content = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")
    return f"hop:basal-processing-geometry/{hashlib.sha256(content).hexdigest()}@1"


class BasalProcessingGeometryHit(BasalProcessingGeometryFeasibility):
    """One compatible geometry in canonical, policy-neutral order."""

    candidate_id: str = Field(pattern=r"^hop:basal-processing-geometry/[0-9a-f]{64}@1$")
    canonical_ordinal: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_hit(self) -> BasalProcessingGeometryHit:
        if not self.compatible:
            raise ValueError("A basal processing geometry hit must be compatible.")
        feasibility = BasalProcessingGeometryFeasibility.model_validate(
            self.model_dump(mode="python", exclude={"candidate_id", "canonical_ordinal"})
        )
        if self.candidate_id != basal_processing_geometry_id(feasibility):
            raise ValueError("Basal processing candidate_id must match its geometry content.")
        return self


def basal_processing_hit_order_key(hit: BasalProcessingGeometryHit) -> tuple[object, ...]:
    """Return deterministic physical order without study desirability."""
    return (
        hit.nicking_agent_id,
        hit.orientation,
        hit.nick_site_start,
        hit.nick_site_end,
        hit.candidate_id,
    )


class BasalProcessingGeometrySearchLimits(HopModel):
    """Hard budgets for evaluated nicking agents and returned geometries."""

    max_search_nodes: int = Field(ge=1)
    max_hits: int = Field(ge=1)


class BasalProcessingGeometrySearchResult(HopModel):
    """Bounded exact-terminal geometry search with complete per-agent evidence."""

    status: BasalProcessingGeometryStatus
    catalog_id: ReferenceId
    request: BasalProcessingGeometryRequest
    limits: BasalProcessingGeometrySearchLimits
    release: BasalReleaseGeometry
    hits: tuple[BasalProcessingGeometryHit, ...]
    feasibility: tuple[BasalProcessingGeometryFeasibility, ...]
    candidate_space_size: int = Field(ge=0)
    search_nodes_examined: int = Field(ge=0)
    observed_hit_count: int = Field(ge=0)
    truncated_by: tuple[BasalProcessingGeometryTruncation, ...] = ()

    @model_validator(mode="after")
    def validate_search(self) -> BasalProcessingGeometrySearchResult:
        expected_examined = min(self.candidate_space_size, self.limits.max_search_nodes)
        if self.search_nodes_examined != expected_examined:
            raise ValueError("search_nodes_examined must exhaust the available node budget.")
        if len(self.feasibility) != self.search_nodes_examined:
            raise ValueError("Feasibility rows must equal examined search nodes.")
        agent_ids = tuple(row.nicking_agent_id for row in self.feasibility)
        if agent_ids != tuple(sorted(agent_ids)) or len(set(agent_ids)) != len(agent_ids):
            raise ValueError("Feasibility rows must contain unique agents in canonical order.")
        compatible_rows = tuple(row for row in self.feasibility if row.compatible)
        if self.observed_hit_count != len(compatible_rows):
            raise ValueError("observed_hit_count must equal compatible feasibility rows.")
        expected_returned = min(self.observed_hit_count, self.limits.max_hits)
        if len(self.hits) != expected_returned:
            raise ValueError("Returned hits must exhaust the available hit budget.")
        if tuple(hit.canonical_ordinal for hit in self.hits) != tuple(range(1, len(self.hits) + 1)):
            raise ValueError("Returned hit ordinals must be contiguous and one-based.")
        if self.hits != tuple(sorted(self.hits, key=basal_processing_hit_order_key)):
            raise ValueError("Returned hits must use canonical physical order.")
        expected_ids = tuple(
            basal_processing_geometry_id(row) for row in compatible_rows[: self.limits.max_hits]
        )
        if tuple(hit.candidate_id for hit in self.hits) != expected_ids:
            raise ValueError("Returned hits must project the compatible feasibility rows.")

        expected_truncation: list[BasalProcessingGeometryTruncation] = []
        if self.search_nodes_examined < self.candidate_space_size:
            expected_truncation.append("max_search_nodes")
        if self.observed_hit_count > self.limits.max_hits:
            expected_truncation.append("max_hits")
        if self.truncated_by != tuple(expected_truncation):
            raise ValueError("truncated_by must exactly describe node and hit truncation.")
        if (self.status == "truncated") != bool(self.truncated_by):
            raise ValueError("Truncated status and truncation evidence must agree.")
        if self.status == "complete" and not self.hits:
            raise ValueError("A complete search must return compatible geometries.")
        if self.status == "infeasible":
            if self.search_nodes_examined != self.candidate_space_size:
                raise ValueError("An infeasible search must examine the complete candidate space.")
            if self.observed_hit_count or self.hits:
                raise ValueError("An infeasible search cannot contain compatible geometries.")

        if self.release.release_agent_id != self.request.release_agent_id:
            raise ValueError("Resolved release geometry must match the request agent.")
        if self.release.orientation is not self.request.release_orientation:
            raise ValueError("Resolved release geometry must match the request orientation.")
        if self.request.require_release_site_excised and not self.release.recognition_site_excised:
            raise ValueError("The request requires the release recognition site to be excised.")
        expected_post_coordinates = tuple(range(4, 4 + len(self.request.post_nick_template)))
        for row in self.feasibility:
            if row.release_agent_id != self.release.release_agent_id:
                raise ValueError("Every feasibility row must use the resolved release geometry.")
            if row.nicked_strand is not self.request.terminal_nicked_strand:
                raise ValueError("Every feasibility row must nick the requested strand.")
            if tuple(domain.relative_coordinate for domain in row.post_nick_domains) != (
                expected_post_coordinates
            ):
                raise ValueError("Post-nick domains must cover the caller-authored template.")
            for domain, symbol in zip(
                row.retained_scar_domains,
                self.request.retained_scar_template,
                strict=True,
            ):
                if not set(domain.allowed_bases) <= iupac_bases(symbol):
                    raise ValueError("Retained scar geometry lies outside the caller domain.")
            if self.request.post_nick_domain_mode == "preserve" and row.compatible:
                for domain, symbol in zip(
                    row.post_nick_domains,
                    self.request.post_nick_template,
                    strict=True,
                ):
                    if set(domain.allowed_bases) != iupac_bases(symbol):
                        raise ValueError(
                            "Compatible preserve-mode geometry narrowed the post-nick domain."
                        )
        return self


__all__ = [
    "BasalProcessingGeometryBlocker",
    "BasalProcessingGeometryFeasibility",
    "BasalProcessingGeometryHit",
    "BasalProcessingGeometryRequest",
    "BasalProcessingGeometrySearchLimits",
    "BasalProcessingGeometrySearchResult",
    "BasalProcessingGeometryTruncation",
    "BasalReleaseGeometry",
    "RelativeBaseDomain",
]
