"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal/result.py

Defines the lossless relation between basal discovery and exact route records.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction import (
    NeighborhoodDiscoveryResult,
    PayloadCompatibilityStatus,
    SearchFeasibilityStatus,
)
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.reaction_replay import assess_reaction_program
from hop_design.models.sequence import iupac_bases
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .realization import BasalRealizationRecord


class BasalNeighborhoodDiscoveryResult(HopModel):
    """Shared discovery authority plus lossless exact basal route records."""

    schema_id: Literal["hop.basal-neighborhood-result/v4"] = Field(
        default="hop.basal-neighborhood-result/v4", alias="schema"
    )
    result_id: str = Field(pattern=r"^hop:basal-neighborhood-result/[0-9a-f]{64}@1$")
    discovery: NeighborhoodDiscoveryResult
    realizations: tuple[BasalRealizationRecord, ...]

    @classmethod
    def create(cls, **content: object) -> BasalNeighborhoodDiscoveryResult:
        draft = cls.model_construct(result_id="", **cast(Any, content))
        return cls.model_validate({"result_id": draft._expected_result_id(), **content})

    def _expected_result_id(self) -> str:
        seed = {
            "schema": self.schema_id,
            "discovery_result_id": self.discovery.result_id,
            "basal_realization_ids": [item.basal_realization_id for item in self.realizations],
        }
        digest = sha256_digest(canonical_json_bytes(seed)).removeprefix("sha256:")
        return f"hop:basal-neighborhood-result/{digest}@1"

    @model_validator(mode="after")
    def validate_relation(self) -> BasalNeighborhoodDiscoveryResult:
        NeighborhoodDiscoveryResult.model_validate(self.discovery.model_dump(mode="python"))
        if self.result_id != self._expected_result_id():
            raise ValueError("result_id must seal the complete basal neighborhood result.")
        discovery_ids = tuple(item.local_realization_id for item in self.discovery.realizations)
        detail_ids = tuple(
            item.local_realization.local_realization_id for item in self.realizations
        )
        if discovery_ids != detail_ids:
            raise ValueError("Basal records must preserve every discovery realization in order.")
        if any(
            item.projection.endpoint is not self.discovery.request.endpoint
            for item in self.realizations
        ):
            raise ValueError("Every basal projection must use the requested endpoint.")
        accounting = self.discovery.payload_compatibility
        if accounting.status is PayloadCompatibilityStatus.COMPLETE:
            detailed_payloads = {item.payload_sequence for item in self.realizations}
            if (
                self.discovery.disposition.feasibility is SearchFeasibilityStatus.FEASIBLE
                and len(detailed_payloads) != accounting.compatible_assignments
            ):
                raise ValueError(
                    "Complete basal accounting must equal the distinct compatible payload records."
                )
            if (
                self.discovery.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
                and not self.discovery.request.hard_constraints.require_all_members_compatible
                and accounting.compatible_assignments != 0
            ):
                raise ValueError(
                    "Non-require-all infeasible payload accounting must report zero compatible "
                    "assignments."
                )
        request = self.discovery.request
        requested = request.payload.payload.sequence
        for item in self.realizations:
            if len(item.payload_sequence) != len(requested) or any(
                base not in iupac_bases(symbol)
                for base, symbol in zip(item.payload_sequence, requested, strict=True)
            ):
                raise ValueError("Every basal detail must bind to the exact request payload.")
            if (
                len(item.payload_source_map.segments) != 1
                or item.payload_source_map.segments[0].payload_span.start
                != request.payload.basal_boundary
                or item.payload_source_map.segments[0].payload_span.end
                != request.payload.foldback_boundary
            ):
                raise ValueError(
                    "Every basal detail source mapping must bind to the request payload span."
                )
            operation_count = sum(
                len(stage.operations)
                for program in item.reaction_programs
                for stage in program.stages
            )
            if item.future_release_action is not None:
                operation_count += 1
                if not request.enzyme_provisioning.permits(
                    item.future_release_action.enzyme_id,
                    role=EnzymeRole.END_GENERATION,
                ):
                    raise ValueError(
                        "Basal future release action violates its provisioning policy."
                    )
            max_operations = request.enzyme_provisioning.max_operations
            if max_operations is not None and operation_count > max_operations:
                raise ValueError(
                    "Basal realization violates the local provisioning operation limit."
                )
            if any(
                assess_reaction_program(
                    program=program,
                    policy=request.enzyme_provisioning,
                ).report.has_errors
                for program in item.reaction_programs
            ):
                raise ValueError("Basal realization violates its exact provisioning policy.")
        return self
