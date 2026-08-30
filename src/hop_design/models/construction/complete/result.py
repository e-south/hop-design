"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/result.py

Defines exact materialized construction records and complete-space accounting.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from itertools import islice, product
from typing import Any, Literal, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.accounting import (
    FailureReasonCount,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
    ProjectionInventoryItem,
    RealizationGroup,
    RealizationGrouping,
    SearchCompletionStatus,
)
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.payload import _content_id

from .accounting import CompositionAccounting, validate_realization_groups
from .authority import (
    CompositionDisposition,
    CompositionDispositionStatus,
    CompositionMaterialAccounting,
    ConstructionCompositionExecution,
    ConstructionCompositionProvenance,
)
from .local_authority import validate_local_authority_compatibility
from .realization import MaterializedConstructionRealization
from .request import ConstructionDiscoveryRequest
from .source_authority import validate_result_authorities
from .validation import (
    expected_accounting,
    expected_material_accounting,
    validate_accepted_realization,
    validate_combination_evaluations,
    validate_endpoint_evidence,
)


class ConstructionSpaceResult(HopModel):
    """Truthful bounded whole-route result with reversible exact grouping."""

    schema_id: Literal["hop.construction-space-result/v2"] = Field(
        default="hop.construction-space-result/v2", alias="schema"
    )
    result_id: str = Field(pattern=r"^hop:construction-space-result/[0-9a-f]{64}@1$")
    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    execution_id: str = Field(pattern=r"^hop:construction-execution/[0-9a-f]{64}@1$")
    execution: ConstructionCompositionExecution
    status: SearchCompletionStatus
    request: ConstructionDiscoveryRequest
    foldback_authority: FoldbackNeighborhoodDiscoveryResult
    basal_authority: BasalNeighborhoodDiscoveryResult | None = None
    realizations: tuple[MaterializedConstructionRealization, ...]
    geometry_groups: tuple[RealizationGroup, ...]
    final_product_groups: tuple[RealizationGroup, ...]
    accounting: CompositionAccounting
    failure_reasons: tuple[FailureReasonCount, ...]
    truncation_reasons: tuple[str, ...] = ()
    upstream_truncation_reasons: tuple[str, ...] = ()
    provenance: ConstructionCompositionProvenance
    projection_inventory: tuple[ProjectionInventoryItem, ...]
    material_accounting: CompositionMaterialAccounting
    claim_boundary: NeighborhoodClaimBoundary
    combination_dispositions: tuple[CompositionDisposition, ...]

    @classmethod
    def create(cls, **content: object) -> ConstructionSpaceResult:
        draft = cls.model_construct(result_id="", **cast(Any, content))
        return cls.model_validate({"result_id": draft._expected_result_id(), **content})

    def _expected_result_id(self) -> str:
        content = {
            "schema": self.schema_id,
            "problem_id": self.problem_id,
            "execution_id": self.execution_id,
            "status": self.status,
            "realization_ids": tuple(
                item.materialized_realization_id for item in self.realizations
            ),
            "geometry_groups": tuple(item.model_dump(mode="json") for item in self.geometry_groups),
            "final_product_groups": tuple(
                item.model_dump(mode="json") for item in self.final_product_groups
            ),
            "accounting": self.accounting.model_dump(mode="json"),
            "failure_reasons": tuple(item.model_dump(mode="json") for item in self.failure_reasons),
            "truncation_reasons": self.truncation_reasons,
            "upstream_truncation_reasons": self.upstream_truncation_reasons,
            "provenance": self.provenance.model_dump(mode="json"),
            "material_accounting": self.material_accounting.model_dump(mode="json"),
            "claim_boundary": self.claim_boundary.model_dump(mode="json"),
            "combination_dispositions": tuple(
                item.model_dump(mode="json") for item in self.combination_dispositions
            ),
        }
        return _content_id("construction-space-result", 1, content)

    @model_validator(mode="after")
    def validate_result(self) -> ConstructionSpaceResult:
        ConstructionDiscoveryRequest.model_validate(self.request.model_dump(mode="python"))
        if self.problem_id != self.request.problem_id:
            raise ValueError("Construction problem identity must replay the exact request.")
        if (
            self.execution.problem_id != self.problem_id
            or self.execution.enumeration != self.request.enumeration
            or self.execution.execution_id != self.execution_id
        ):
            raise ValueError("Construction execution identity must replay exact execution facts.")
        if (
            self.provenance.foldback_result_id != self.request.foldback_result_id
            or self.provenance.basal_result_id != self.request.basal_result_id
            or self.provenance.design_bundle_id != self.request.design.bundle.bundle_id
        ):
            raise ValueError(
                "Construction provenance must bind every requested upstream authority."
            )
        if self.provenance.hop_version != self.execution.hop_version:
            raise ValueError("Provenance HOP version must equal the execution HOP version.")
        validate_result_authorities(
            request=self.request,
            provenance=self.provenance,
            foldback=self.foldback_authority,
            basal=self.basal_authority,
            realizations=self.realizations,
        )
        validate_local_authority_compatibility(
            self.request,
            foldback=self.foldback_authority,
            basal=self.basal_authority,
        )
        expected_upstream_reasons = tuple(
            f"foldback:{reason}"
            for reason in self.foldback_authority.neighborhood.truncation_reasons
        ) + tuple(
            f"basal:{reason}"
            for reason in (
                ()
                if self.basal_authority is None
                else self.basal_authority.discovery.truncation_reasons
            )
        )
        if self.upstream_truncation_reasons != expected_upstream_reasons:
            raise ValueError(
                "Upstream truncation reasons must replay exact local authorities in order."
            )
        ids = tuple(item.materialized_realization_id for item in self.realizations)
        if len(ids) != len(set(ids)):
            raise ValueError("Complete construction results must not repeat realizations.")
        if self.status is SearchCompletionStatus.COMPLETE and not ids:
            raise ValueError("Complete construction results require exact realizations.")
        if self.status is SearchCompletionStatus.INFEASIBLE and ids:
            raise ValueError("Infeasible construction results must not contain realizations.")
        if len(self.failure_reasons) != len({item.code for item in self.failure_reasons}):
            raise ValueError("Construction failure-reason codes must be unique.")
        if tuple(item.code for item in self.failure_reasons) != tuple(
            sorted(item.code for item in self.failure_reasons)
        ):
            raise ValueError("Construction failure reasons must use canonical code order.")
        if len(self.truncation_reasons) != len(set(self.truncation_reasons)):
            raise ValueError("Construction truncation-reason codes must be unique.")
        if self.accounting.valid_realizations != len(ids):
            raise ValueError("Composition accounting must match exact realization count.")
        if (
            self.status
            in {
                SearchCompletionStatus.COMPLETE,
                SearchCompletionStatus.INFEASIBLE,
            }
            and self.accounting.examined_combinations != self.accounting.nominal_combinations
        ):
            raise ValueError("Non-truncated results must examine the complete nominal product.")
        validate_realization_groups(
            self.geometry_groups,
            self.realizations,
            RealizationGrouping.ACHIEVED_GEOMETRY,
        )
        validate_realization_groups(
            self.final_product_groups,
            self.realizations,
            RealizationGrouping.FINAL_PRODUCT,
        )
        if self.accounting.distinct_geometry_groups != len(self.geometry_groups) or (
            self.accounting.distinct_final_products != len(self.final_product_groups)
        ):
            raise ValueError("Composition accounting must match reversible grouping counts.")
        if sum(item.count for item in self.failure_reasons) < self.accounting.rejected_combinations:
            raise ValueError("Failure reasons must account for every rejected combination.")
        if len(self.combination_dispositions) != self.accounting.examined_combinations:
            raise ValueError("Combination dispositions must cover the exact examined prefix.")
        if tuple(item.ordinal for item in self.combination_dispositions) != tuple(
            range(len(self.combination_dispositions))
        ):
            raise ValueError("Combination dispositions must preserve canonical Cartesian order.")
        basal_domain: tuple[str | None, ...] = (
            (None,)
            if self.request.basal_result_id is None
            else tuple(self.provenance.basal_realization_ids)
        )
        expected_pairs = tuple(
            islice(
                product(self.provenance.foldback_realization_ids, basal_domain),
                len(self.combination_dispositions),
            )
        )
        observed_pairs = tuple(
            (item.foldback_realization_id, item.basal_realization_id)
            for item in self.combination_dispositions
        )
        if observed_pairs != expected_pairs:
            raise ValueError("Combination dispositions must replay the ordered upstream domains.")
        statuses = tuple(item.status for item in self.combination_dispositions)
        examined = len(statuses)
        accepted = tuple(
            item.materialized_realization_id
            for item in self.combination_dispositions
            if item.status is CompositionDispositionStatus.ACCEPTED
        )
        rejected = Counter(
            item.rejection_reason
            for item in self.combination_dispositions
            if item.status is CompositionDispositionStatus.REJECTED
        )
        replayed_accounting = expected_accounting(
            provenance=self.provenance,
            dispositions=self.combination_dispositions,
            geometry_group_count=len(self.geometry_groups),
            final_product_group_count=len(self.final_product_groups),
        )
        if any(
            getattr(self.accounting, key) != value for key, value in replayed_accounting.items()
        ):
            raise ValueError("Composition accounting must replay exact result dispositions.")
        if examined != self.accounting.examined_combinations or accepted != ids:
            raise ValueError(
                "Combination dispositions must reconcile examined and accepted counts."
            )
        if rejected != Counter({item.code: item.count for item in self.failure_reasons}):
            raise ValueError("Rejected dispositions must reconcile exact failure counts.")
        validate_combination_evaluations(
            request=self.request,
            foldback_authority=self.foldback_authority,
            basal_authority=self.basal_authority,
            dispositions=self.combination_dispositions,
            realizations=self.realizations,
        )
        if self.request.whole_route_constraints.require_all_combinations_valid:
            if self.status is SearchCompletionStatus.COMPLETE and (
                any(item is not CompositionDispositionStatus.ACCEPTED for item in statuses)
                or not ids
            ):
                raise ValueError(
                    "The all combinations constraint requires a complete accepted space."
                )
            if self.status is SearchCompletionStatus.INFEASIBLE and any(
                item is not CompositionDispositionStatus.REJECTED for item in statuses
            ):
                raise ValueError(
                    "An all-combinations infeasible result must reject the complete space."
                )
        dispositions_by_id = {
            item.materialized_realization_id: item
            for item in self.combination_dispositions
            if item.materialized_realization_id is not None
        }
        for realization in self.realizations:
            validate_endpoint_evidence(self.request, realization)
            validate_accepted_realization(
                request=self.request,
                provenance=self.provenance,
                disposition=dispositions_by_id[realization.materialized_realization_id],
                realization=realization,
            )
        if self.material_accounting != expected_material_accounting(self.realizations):
            raise ValueError("Material accounting must derive from exact route materials.")
        expected_local_reason = self._local_truncation_reason()
        expected_local_reasons = () if expected_local_reason is None else (expected_local_reason,)
        if self.truncation_reasons != expected_local_reasons:
            raise ValueError(
                "Local truncation reasons must replay the examined prefix and execution bounds."
            )
        expected_status = (
            SearchCompletionStatus.TRUNCATED
            if expected_local_reason is not None or expected_upstream_reasons
            else SearchCompletionStatus.COMPLETE
            if ids
            else SearchCompletionStatus.INFEASIBLE
        )
        if self.status is not expected_status:
            raise ValueError("Construction status must derive from exact bounded outcomes.")
        expected_method = (
            MethodResolutionStatus.RESOLVED
            if expected_status is SearchCompletionStatus.COMPLETE
            else MethodResolutionStatus.NOT_RESOLVED
        )
        if self.claim_boundary.method is not expected_method:
            raise ValueError("Construction method claim must derive from exact result status.")
        if self.result_id != self._expected_result_id():
            raise ValueError("result_id must seal the complete construction-space result.")
        return self

    def _local_truncation_reason(self) -> str | None:
        examined = len(self.combination_dispositions)
        nominal = self.accounting.nominal_combinations
        if examined == nominal:
            return None
        if examined > nominal:
            raise ValueError("Examined composition prefix cannot exceed the nominal product.")
        if examined == self.execution.enumeration.max_combinations:
            return "max_combinations"
        if len(self.realizations) == self.execution.enumeration.max_realizations:
            return "max_realizations"
        raise ValueError(
            "A partial composition prefix must identify the exact execution bound that fired."
        )


__all__ = [
    "CompositionAccounting",
    "ConstructionSpaceResult",
]
