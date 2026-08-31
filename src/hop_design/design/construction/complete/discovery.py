"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/discovery.py

Composes exact local construction authorities into bounded complete routes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import islice, product

from hop_design.design.bundle import VerifiedHopBundle, verify_hop_bundle_semantics
from hop_design.design.construction.verification import (
    VerifiedBasalNeighborhoodResult,
    VerifiedFoldbackNeighborhoodResult,
)
from hop_design.models.construction import SearchCompletionStatus
from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
)
from hop_design.models.construction.complete import (
    CompositionDisposition,
    CompositionDispositionStatus,
    ConstructionDiscoveryRequest,
    ConstructionSpaceResult,
    MaterializedConstructionRealization,
)
from hop_design.models.construction.complete.evaluation import (
    CompositionRejectionCode,
    evaluate_combination,
)
from hop_design.models.construction.complete.local_authority import (
    validate_local_authority_compatibility,
)
from hop_design.models.construction.complete.source_authority import (
    expected_upstream_truncation_reasons,
)
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.source_partition import SourcePartitionDiscoveryResult

from .design_authority import assert_design_authority
from .endpoint import materialize_endpoint
from .partition_binding import (
    bind_partition_to_realization,
    source_partition_enzyme_policies,
    validate_partition_selection,
)
from .results import build_result
from .selection import select_local_domains, validate_detailed_authority_ids


@dataclass(frozen=True)
class VerifiedConstructionSpaceResult:
    """Whole construction result admitted after deterministic composition replay."""

    result: ConstructionSpaceResult
    foldback: VerifiedFoldbackNeighborhoodResult
    basal: VerifiedBasalNeighborhoodResult | None
    design: VerifiedHopBundle

    def __post_init__(self) -> None:
        parsed, foldback, basal = _replay_construction_result(
            self.result,
            foldback=self.foldback,
            basal=self.basal,
            design=self.design,
        )
        object.__setattr__(self, "result", parsed)
        object.__setattr__(self, "foldback", foldback)
        object.__setattr__(self, "basal", basal)


def _discover_constructions_raw(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackNeighborhoodDiscoveryResult,
    basal: BasalNeighborhoodDiscoveryResult | None,
    design: VerifiedHopBundle,
    source_partition: SourcePartitionDiscoveryResult | None = None,
) -> ConstructionSpaceResult:
    """Compose every exact compatible local combination within declared bounds."""
    assert_design_authority(request, design)
    validate_local_authority_compatibility(request, foldback=foldback, basal=basal)
    validate_detailed_authority_ids(request, foldback=foldback, basal=basal)
    source_partition = validate_partition_selection(request, source_partition)
    enzyme_policies = source_partition_enzyme_policies(foldback, basal)
    foldback_records, basal_records = select_local_domains(
        request,
        foldback=foldback,
        basal=basal,
    )
    nominal = len(foldback_records) * len(basal_records)
    records: list[MaterializedConstructionRealization] = []
    partition_rejection_candidates: list[MaterializedConstructionRealization] = []
    failures: Counter[str] = Counter()
    examined = 0
    truncation: str | None = None
    dispositions: list[CompositionDisposition] = []
    for ordinal, (foldback_record, basal_record) in enumerate(
        islice(
            product(foldback_records, basal_records),
            request.enumeration.max_combinations,
        )
    ):
        if len(records) >= request.enumeration.max_realizations:
            truncation = "max_realizations"
            break
        examined += 1
        evaluation = evaluate_combination(
            request,
            foldback=foldback_record,
            basal=basal_record,
            foldback_policy=foldback.neighborhood.request.enzyme_provisioning,
            basal_policy=(None if basal is None else basal.discovery.request.enzyme_provisioning),
        )
        if evaluation.truncation_reason is not None:
            dispositions.append(
                CompositionDisposition(
                    ordinal=ordinal,
                    foldback_realization_id=foldback_record.foldback_realization_id,
                    basal_realization_id=(
                        None if basal_record is None else basal_record.basal_realization_id
                    ),
                    status=CompositionDispositionStatus.TRUNCATED,
                    truncation_reason=evaluation.truncation_reason,
                    candidate_enzyme_programs=evaluation.candidate_enzyme_programs,
                    recognition_placements_attempted=(evaluation.recognition_placements_attempted),
                    constraint_systems_attempted=evaluation.constraint_systems_attempted,
                )
            )
            continue
        record = materialize_endpoint(
            request,
            foldback=foldback_record,
            basal=basal_record,
            foldback_result=foldback,
            basal_result=basal,
            evaluation=evaluation,
        )
        resolved_record: MaterializedConstructionRealization | CompositionRejectionCode = record
        if not isinstance(record, CompositionRejectionCode):
            partition_outcome = bind_partition_to_realization(
                request=request,
                realization=record,
                authority=source_partition,
                enzyme_policies=enzyme_policies,
            )
            if partition_outcome.rejection_candidate is not None:
                partition_rejection_candidates.append(partition_outcome.rejection_candidate)
            if partition_outcome.rejection_reason is not None:
                resolved_record = partition_outcome.rejection_reason
            elif partition_outcome.realization is not None:
                resolved_record = partition_outcome.realization
            else:
                raise AssertionError("Partition binding must return one exact outcome.")
        if isinstance(resolved_record, CompositionRejectionCode):
            failures[resolved_record] += 1
            dispositions.append(
                CompositionDisposition(
                    ordinal=ordinal,
                    foldback_realization_id=foldback_record.foldback_realization_id,
                    basal_realization_id=(
                        None if basal_record is None else basal_record.basal_realization_id
                    ),
                    status=CompositionDispositionStatus.REJECTED,
                    rejection_reason=resolved_record,
                    candidate_enzyme_programs=evaluation.candidate_enzyme_programs,
                    recognition_placements_attempted=(evaluation.recognition_placements_attempted),
                    constraint_systems_attempted=evaluation.constraint_systems_attempted,
                )
            )
            continue
        records.append(resolved_record)
        dispositions.append(
            CompositionDisposition(
                ordinal=ordinal,
                foldback_realization_id=foldback_record.foldback_realization_id,
                basal_realization_id=(
                    None if basal_record is None else basal_record.basal_realization_id
                ),
                status=CompositionDispositionStatus.ACCEPTED,
                materialized_realization_id=resolved_record.materialized_realization_id,
                candidate_enzyme_programs=evaluation.candidate_enzyme_programs,
                recognition_placements_attempted=(evaluation.recognition_placements_attempted),
                constraint_systems_attempted=evaluation.constraint_systems_attempted,
            )
        )
    if truncation is None and examined < nominal:
        truncation = "max_combinations"
    endpoint_truncation_reasons = tuple(
        dict.fromkeys(
            item.truncation_reason for item in dispositions if item.truncation_reason is not None
        )
    )
    exact = tuple(records)
    if (
        request.whole_route_constraints.require_all_combinations_valid
        and failures
        and exact
        and not truncation
        and foldback.neighborhood.status is not SearchCompletionStatus.TRUNCATED
        and (basal is None or basal.discovery.status is not SearchCompletionStatus.TRUNCATED)
    ):
        failures[CompositionRejectionCode.ALL_COMBINATIONS_VALID_REQUIRED] += len(exact)
        dispositions = [
            CompositionDisposition(
                ordinal=item.ordinal,
                foldback_realization_id=item.foldback_realization_id,
                basal_realization_id=item.basal_realization_id,
                status=CompositionDispositionStatus.REJECTED,
                rejection_reason=(
                    CompositionRejectionCode.ALL_COMBINATIONS_VALID_REQUIRED
                    if item.status is CompositionDispositionStatus.ACCEPTED
                    else item.rejection_reason
                ),
                candidate_enzyme_programs=item.candidate_enzyme_programs,
                recognition_placements_attempted=item.recognition_placements_attempted,
                constraint_systems_attempted=item.constraint_systems_attempted,
            )
            for item in dispositions
        ]
        exact = ()
    upstream_truncation_reasons = expected_upstream_truncation_reasons(
        request=request,
        foldback=foldback,
        basal=basal,
    )
    status = (
        SearchCompletionStatus.TRUNCATED
        if truncation or endpoint_truncation_reasons or upstream_truncation_reasons
        else SearchCompletionStatus.COMPLETE
        if exact
        else SearchCompletionStatus.INFEASIBLE
    )
    return build_result(
        request=request,
        status=status,
        realizations=exact,
        failures=failures,
        truncation=truncation,
        endpoint_truncation_reasons=endpoint_truncation_reasons,
        upstream_truncation_reasons=upstream_truncation_reasons,
        foldback_count=len(foldback_records),
        basal_count=(0 if basal is None else len(basal_records)),
        nominal=nominal,
        examined=examined,
        foldback_authority=foldback,
        basal_authority=basal,
        source_partition_authority=source_partition,
        source_partition_rejection_candidates=tuple(partition_rejection_candidates),
        design_bundle_id=design.bundle.bundle_id,
        dispositions=tuple(dispositions),
    )


def verify_construction_space_result(
    result: ConstructionSpaceResult,
    *,
    foldback: VerifiedFoldbackNeighborhoodResult,
    basal: VerifiedBasalNeighborhoodResult | None,
    design: VerifiedHopBundle,
) -> VerifiedConstructionSpaceResult:
    """Rerun exact whole-route composition and admit only canonical-byte equality."""
    return VerifiedConstructionSpaceResult(
        result=result,
        foldback=foldback,
        basal=basal,
        design=design,
    )


def _replay_construction_result(
    result: ConstructionSpaceResult,
    *,
    foldback: VerifiedFoldbackNeighborhoodResult,
    basal: VerifiedBasalNeighborhoodResult | None,
    design: VerifiedHopBundle,
) -> tuple[
    ConstructionSpaceResult,
    VerifiedFoldbackNeighborhoodResult,
    VerifiedBasalNeighborhoodResult | None,
]:
    from hop_design.serialization import canonical_json_bytes

    if not isinstance(foldback, VerifiedFoldbackNeighborhoodResult) or (
        basal is not None and not isinstance(basal, VerifiedBasalNeighborhoodResult)
    ):
        raise TypeError("Construction replay requires verified local construction authorities.")
    verify_hop_bundle_semantics(design)
    foldback_result = foldback._verified_result()
    basal_result = None if basal is None else basal._verified_result()
    parsed = ConstructionSpaceResult.model_validate(result.model_dump(mode="python"))
    expected = _discover_constructions_raw(
        parsed.request,
        foldback=foldback_result,
        basal=basal_result,
        design=design,
        source_partition=parsed.source_partition_authority,
    )
    if canonical_json_bytes(expected) != canonical_json_bytes(parsed):
        raise ValueError(
            "Construction space result disagrees with deterministic composition replay."
        )
    return parsed, foldback, basal


def discover_constructions(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: VerifiedFoldbackNeighborhoodResult,
    basal: VerifiedBasalNeighborhoodResult | None,
    design: VerifiedHopBundle,
    source_partition: SourcePartitionDiscoveryResult | None = None,
) -> VerifiedConstructionSpaceResult:
    """Compose and verify every exact compatible local combination within declared bounds."""
    if not isinstance(foldback, VerifiedFoldbackNeighborhoodResult) or (
        basal is not None and not isinstance(basal, VerifiedBasalNeighborhoodResult)
    ):
        raise TypeError("Complete composition requires verified local construction authorities.")
    verify_hop_bundle_semantics(design)
    foldback_result = foldback._verified_result()
    basal_result = None if basal is None else basal._verified_result()
    raw = _discover_constructions_raw(
        request,
        foldback=foldback_result,
        basal=basal_result,
        design=design,
        source_partition=source_partition,
    )
    return verify_construction_space_result(
        raw,
        foldback=foldback,
        basal=basal,
        design=design,
    )


__all__ = [
    "VerifiedConstructionSpaceResult",
    "discover_constructions",
    "verify_construction_space_result",
]
