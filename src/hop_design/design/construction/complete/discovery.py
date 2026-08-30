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
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)
from hop_design.models.construction import SearchCompletionStatus
from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
    BasalRealizationRecord,
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
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult

from .endpoint import materialize_endpoint
from .results import build_result


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


def _assert_design_reference(
    request: ConstructionDiscoveryRequest,
    design: VerifiedHopBundle,
) -> None:
    encoding = design.plan.hairpin_encoding_insert
    observed = (
        design.bundle.bundle_id,
        design.spec,
        design.plan,
        design.plan.plan_id,
        design.plan.design_id,
        design.spec.payload.sequence,
        encoding.sequence,
        encoding.sequence_digest,
    )
    expected = (
        request.design.bundle.bundle_id,
        request.design.spec,
        request.design.plan,
        request.design.plan_id,
        request.design.design_id,
        request.design.payload_sequence,
        request.design.encoding_sequence,
        request.design.encoding_digest,
    )
    if observed != expected:
        raise ValueError("Construction request must bind the exact verified HOP design bundle.")


def _discover_constructions_raw(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: FoldbackNeighborhoodDiscoveryResult,
    basal: BasalNeighborhoodDiscoveryResult | None,
    design: VerifiedHopBundle,
) -> ConstructionSpaceResult:
    """Compose every exact compatible local combination within declared bounds."""
    _assert_design_reference(request, design)
    validate_local_authority_compatibility(request, foldback=foldback, basal=basal)
    if foldback.result_id != request.foldback_result_id:
        raise ValueError("Foldback detailed result identity does not match the request.")
    if (None if basal is None else basal.result_id) != request.basal_result_id:
        raise ValueError("Basal detailed result identity does not match the request.")
    foldback_records = tuple(
        item
        for item in foldback.realizations
        if item.payload_sequence == request.payload.payload.sequence
    )
    basal_records: tuple[BasalRealizationRecord | None, ...] = (
        (None,)
        if basal is None
        else tuple(
            item
            for item in basal.realizations
            if item.payload_sequence == request.payload.payload.sequence
        )
    )
    nominal = len(foldback_records) * len(basal_records)
    records: list[MaterializedConstructionRealization] = []
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
        record = materialize_endpoint(
            request,
            foldback=foldback_record,
            basal=basal_record,
            foldback_result=foldback,
            basal_result=basal,
            evaluation=evaluation,
        )
        if isinstance(record, CompositionRejectionCode):
            failures[record] += 1
            dispositions.append(
                CompositionDisposition(
                    ordinal=ordinal,
                    foldback_realization_id=foldback_record.foldback_realization_id,
                    basal_realization_id=(
                        None if basal_record is None else basal_record.basal_realization_id
                    ),
                    status=CompositionDispositionStatus.REJECTED,
                    rejection_reason=record,
                    candidate_enzyme_programs=evaluation.candidate_enzyme_programs,
                    recognition_placements_attempted=(evaluation.recognition_placements_attempted),
                    constraint_systems_attempted=evaluation.constraint_systems_attempted,
                )
            )
            continue
        records.append(record)
        dispositions.append(
            CompositionDisposition(
                ordinal=ordinal,
                foldback_realization_id=foldback_record.foldback_realization_id,
                basal_realization_id=(
                    None if basal_record is None else basal_record.basal_realization_id
                ),
                status=CompositionDispositionStatus.ACCEPTED,
                materialized_realization_id=record.materialized_realization_id,
                candidate_enzyme_programs=evaluation.candidate_enzyme_programs,
                recognition_placements_attempted=(evaluation.recognition_placements_attempted),
                constraint_systems_attempted=evaluation.constraint_systems_attempted,
            )
        )
    if truncation is None and examined < nominal:
        truncation = "max_combinations"
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
    upstream_truncation_reasons = tuple(
        f"foldback:{reason}"
        for reason in (
            foldback.neighborhood.truncation_reasons
            if foldback.neighborhood.status is SearchCompletionStatus.TRUNCATED
            else ()
        )
    ) + tuple(
        f"basal:{reason}"
        for reason in (
            basal.discovery.truncation_reasons
            if basal is not None and basal.discovery.status is SearchCompletionStatus.TRUNCATED
            else ()
        )
    )
    status = (
        SearchCompletionStatus.TRUNCATED
        if truncation or upstream_truncation_reasons
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
        upstream_truncation_reasons=upstream_truncation_reasons,
        foldback_count=len(foldback_records),
        basal_count=(0 if basal is None else len(basal_records)),
        nominal=nominal,
        examined=examined,
        foldback_authority=foldback,
        basal_authority=basal,
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

    admitted_foldback = verify_foldback_neighborhood_result(foldback.result)
    admitted_basal = None if basal is None else verify_basal_neighborhood_result(basal.result)
    verify_hop_bundle_semantics(design)
    parsed = ConstructionSpaceResult.model_validate(result.model_dump(mode="python"))
    expected = _discover_constructions_raw(
        parsed.request,
        foldback=admitted_foldback.result,
        basal=None if admitted_basal is None else admitted_basal.result,
        design=design,
    )
    if canonical_json_bytes(expected) != canonical_json_bytes(parsed):
        raise ValueError(
            "Construction space result disagrees with deterministic composition replay."
        )
    return parsed, admitted_foldback, admitted_basal


def discover_constructions(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: VerifiedFoldbackNeighborhoodResult,
    basal: VerifiedBasalNeighborhoodResult | None,
    design: VerifiedHopBundle,
) -> VerifiedConstructionSpaceResult:
    """Compose and verify every exact compatible local combination within declared bounds."""
    if not isinstance(foldback, VerifiedFoldbackNeighborhoodResult) or (
        basal is not None and not isinstance(basal, VerifiedBasalNeighborhoodResult)
    ):
        raise TypeError("Complete composition requires verified local construction authorities.")
    foldback = verify_foldback_neighborhood_result(foldback.result)
    basal = None if basal is None else verify_basal_neighborhood_result(basal.result)
    verify_hop_bundle_semantics(design)
    raw = _discover_constructions_raw(
        request,
        foldback=foldback.result,
        basal=None if basal is None else basal.result,
        design=design,
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
