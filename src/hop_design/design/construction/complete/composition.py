"""Derive bounded complete preparations from admitted local authorities."""

from __future__ import annotations

from collections import Counter
from itertools import islice

from hop_design.design.bundle import VerifiedHopBundle
from hop_design.models.construction import SearchCompletionStatus
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.complete import (
    CompositionDisposition,
    CompositionDispositionStatus,
    ConstructionDiscoveryRequest,
    ConstructionSpaceResult,
    MaterializedConstructionRealization,
)
from hop_design.models.construction.complete.composition_domain import (
    composition_domain,
    source_context_count,
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
from hop_design.models.construction.hairpin_geometry import scaffold_mismatches
from hop_design.models.construction.scaffold import ScaffoldMismatch
from hop_design.models.construction.source_partition import SourcePartitionDiscoveryResult

from .design_authority import assert_design_authority
from .endpoint import materialize_endpoint
from .partition_binding import (
    bind_partition_to_realization,
    resolve_partition_plan,
    source_partition_enzyme_policies,
)
from .results import build_result, composition_status, reject_accepted_dispositions
from .selection import select_local_domains, validate_detailed_authority_ids


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
    partition_plan = resolve_partition_plan(request, source_partition)
    enzyme_policies = source_partition_enzyme_policies(foldback, basal)
    foldback_records, basal_records = select_local_domains(request, foldback=foldback, basal=basal)
    source_policy = request.materialization.source_preparation.source_ssdna
    nominal = len(foldback_records) * len(basal_records) * source_context_count(source_policy)
    records: list[MaterializedConstructionRealization] = []
    partition_rejection_candidates: list[MaterializedConstructionRealization] = []
    failures: Counter[str] = Counter()
    examined = 0
    truncation: str | None = None
    dispositions: list[CompositionDisposition] = []
    scaffold_rejection_candidates: list[MaterializedConstructionRealization] = []
    for ordinal, (foldback_record, basal_record, source_context_sequence) in enumerate(
        islice(
            composition_domain(foldback_records, basal_records, source_policy),
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
            source_context_sequence=source_context_sequence,
            source_partition_plan=partition_plan,
        )
        if evaluation.truncation_reason is not None:
            dispositions.append(
                CompositionDisposition(
                    ordinal=ordinal,
                    source_context_sequence=source_context_sequence,
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
            resolved_record = partition_outcome.resolved()
        mismatches: tuple[ScaffoldMismatch, ...] = ()
        if not isinstance(resolved_record, CompositionRejectionCode):
            mismatches = scaffold_mismatches(
                request.whole_route_constraints.hairpin_scaffold, resolved_record
            )
            if mismatches:
                scaffold_rejection_candidates.append(resolved_record)
                resolved_record = CompositionRejectionCode.HAIRPIN_SCAFFOLD_OUTSIDE_REQUEST
        if isinstance(resolved_record, CompositionRejectionCode):
            failures[resolved_record] += 1
            dispositions.append(
                CompositionDisposition(
                    ordinal=ordinal,
                    source_context_sequence=source_context_sequence,
                    foldback_realization_id=foldback_record.foldback_realization_id,
                    basal_realization_id=(
                        None if basal_record is None else basal_record.basal_realization_id
                    ),
                    status=CompositionDispositionStatus.REJECTED,
                    rejection_reason=resolved_record,
                    preparation_constraint=evaluation.preparation_constraint,
                    scaffold_mismatches=mismatches,
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
                source_context_sequence=source_context_sequence,
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
        and foldback.neighborhood.disposition.completion is not SearchCompletionStatus.TRUNCATED
        and (
            basal is None
            or basal.discovery.disposition.completion is not SearchCompletionStatus.TRUNCATED
        )
    ):
        failures[CompositionRejectionCode.ALL_COMBINATIONS_VALID_REQUIRED] += len(exact)
        dispositions = reject_accepted_dispositions(
            dispositions,
            rejection_code=CompositionRejectionCode.ALL_COMBINATIONS_VALID_REQUIRED,
        )
        exact = ()
    upstream_truncation_reasons = expected_upstream_truncation_reasons(
        request=request, foldback=foldback, basal=basal
    )
    status = composition_status(
        realizations=exact,
        truncation=truncation,
        endpoint_truncation_reasons=endpoint_truncation_reasons,
        upstream_truncation_reasons=upstream_truncation_reasons,
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
        scaffold_rejection_candidates=tuple(scaffold_rejection_candidates),
        design_bundle_id=design.bundle.bundle_id,
        dispositions=tuple(dispositions),
    )
