"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/basal/discovery.py

Discovers exact basal constructions across a finite retained-overhead domain.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter, defaultdict
from importlib.metadata import version

from hop_design.kernel.construction.basal import (
    BasalPlacementFailure,
    basal_retained_overhead_nt,
    iter_basal_program_solutions,
    iter_basal_programs,
)
from hop_design.models.construction import (
    BasalGeometryDomain,
    BasalTarget,
    ConstructionExecution,
    DigitalDesignStatus,
    FailureReasonCount,
    LocalNeighborhoodFamily,
    LocalNeighborhoodRequest,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
    NeighborhoodDiscoveryResult,
    NeighborhoodProvenance,
    NickStrandSelection,
    OverheadLevelSummary,
    SearchStopMode,
    SearchTerminationReason,
    problem_id,
)
from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
    BasalRealizationRecord,
)
from hop_design.models.junction import Strand

from ..neighborhood_accounting import (
    payload_accounting,
    payload_assignments,
    payload_cardinality,
    reject_partial_payload_routes,
    search_disposition,
)
from ..sequence_domain import partition_payload_accounting, partition_sequence_domain
from .reactions import _ROUTE_VERSION
from .realization import _groups, _realization


def _exact_strand_targets(target: BasalTarget) -> tuple[BasalTarget, ...]:
    if target.nick_strand is not NickStrandSelection.ANY:
        return (target,)
    return tuple(target.model_copy(update={"nick_strand": strand}) for strand in Strand)


def discover_basal_neighborhood(
    request: LocalNeighborhoodRequest,
) -> BasalNeighborhoodDiscoveryResult:
    """Return exact basal realizations within the declared finite local domain."""
    if request.family is not LocalNeighborhoodFamily.BASAL or not isinstance(
        request.geometry_domain, BasalGeometryDomain
    ):
        raise ValueError("Basal discovery requires a basal geometry domain.")

    payload_total = payload_cardinality(request)
    records: list[BasalRealizationRecord] = []
    levels: list[OverheadLevelSummary] = []
    failures: Counter[str] = Counter()
    compatible_payloads: set[str] = set()
    payload_failures: dict[str, set[str]] = defaultdict(set)
    examined = 0
    rejected = 0
    termination: SearchTerminationReason | None = None
    exact_targets = request.geometry_domain.exact_targets()

    for retained_overhead_nt in range(request.search.max_retained_overhead_nt + 1):
        level_ids: list[str] = []
        level_failures: Counter[str] = Counter()
        level_rejected = 0
        for target in exact_targets:
            for exact_target in _exact_strand_targets(target):
                routes = iter_basal_programs(
                    request.enzyme_provisioning,
                    target=exact_target,
                    endpoint=request.endpoint,
                )
                for payload_sequence in payload_assignments(request):
                    for route in routes:
                        if (
                            basal_retained_overhead_nt(
                                target=exact_target,
                                endpoint=request.endpoint,
                                program=route,
                            )
                            != retained_overhead_nt
                        ):
                            continue
                        solutions = partition_sequence_domain(
                            iter_basal_program_solutions(
                                payload_sequence=payload_sequence,
                                target=exact_target,
                                endpoint=request.endpoint,
                                program=route,
                            ),
                            request.search.sequence_partition,
                        )
                        for solution in solutions:
                            if examined >= request.search.max_search_nodes:
                                termination = SearchTerminationReason.EVALUATION_CAP
                                break
                            examined += 1
                            if isinstance(solution, BasalPlacementFailure):
                                failures[solution.code] += 1
                                level_failures[solution.code] += 1
                                rejected += 1
                                level_rejected += 1
                                payload_failures[payload_sequence].add(solution.code)
                                continue
                            record = _realization(
                                request=request,
                                payload_sequence=payload_sequence,
                                target=exact_target,
                                route=route,
                                solution=solution,
                            )
                            if isinstance(record, str):
                                failures[record] += 1
                                level_failures[record] += 1
                                rejected += 1
                                level_rejected += 1
                                payload_failures[payload_sequence].add(record)
                                continue
                            if len(records) >= request.search.max_realizations:
                                termination = SearchTerminationReason.EVALUATION_CAP
                                break
                            if (
                                record.retained_overhead.retained_overhead_nt
                                != retained_overhead_nt
                            ):
                                raise RuntimeError(
                                    "Basal search domain and endpoint overhead ledger disagree."
                                )
                            records.append(record)
                            level_ids.append(record.local_realization.local_realization_id)
                            compatible_payloads.add(payload_sequence)
                            if (
                                request.search.stop is SearchStopMode.RESULT_QUOTA
                                and request.search.result_quota is not None
                                and len(records) >= request.search.result_quota
                            ):
                                termination = SearchTerminationReason.RESULT_QUOTA
                                break
                        if termination is not None:
                            break
                    if termination is not None:
                        break
                if termination is not None:
                    break
            if termination is not None:
                break
        levels.append(
            OverheadLevelSummary(
                retained_overhead_nt=retained_overhead_nt,
                examined=True,
                complete=termination is None,
                candidate_count=len(level_ids) + level_rejected,
                realization_ids=tuple(level_ids),
                rejected_count=level_rejected,
                failure_reasons=tuple(
                    FailureReasonCount(code=code, count=count)
                    for code, count in sorted(level_failures.items())
                ),
            )
        )
        if termination is not None:
            break

    exact = tuple(records)
    partition_accounting = partition_payload_accounting(
        request.search.sequence_partition,
        total_assignments=payload_total,
    )
    accounting = payload_accounting(
        request=request,
        has_records=bool(exact),
        compatible_payloads=compatible_payloads,
        payload_failures=payload_failures,
        payload_total=payload_total,
        partition_accounting=partition_accounting,
        incomplete=termination is not None,
        incomplete_warning="Bounded basal discovery did not exhaust route compatibility.",
        recognition_failure_code="recognition-payload-conflict",
        recognition_conflict_code="payload-recognition-conflict",
        no_realization_code="payload-no-basal-realization",
    )
    if (
        termination is None
        and exact
        and request.hard_constraints.require_all_members_compatible
        and accounting.excluded_assignments
    ):
        exact, levels, rejected, failures = reject_partial_payload_routes(
            records=exact,
            levels=levels,
            rejected_count=rejected,
            failures=failures,
        )

    execution = ConstructionExecution(
        problem_id=problem_id(request),
        hop_version=version("hop-design"),
        route_implementation_version=_ROUTE_VERSION,
        search=request.search,
        max_operations=request.enzyme_provisioning.max_operations,
        environment={},
    )
    discovery = NeighborhoodDiscoveryResult(
        disposition=search_disposition(termination=termination, has_results=bool(exact)),
        request=request,
        problem_id=problem_id(request),
        execution_id=execution.execution_id,
        execution=execution,
        overhead_levels=tuple(levels),
        realizations=tuple(item.local_realization for item in exact),
        achieved_geometry_groups=_groups(exact),
        rejected_count=rejected,
        failure_reasons=tuple(
            FailureReasonCount(code=code, count=count) for code, count in sorted(failures.items())
        ),
        payload_compatibility=accounting,
        provenance=NeighborhoodProvenance(
            hop_version=version("hop-design"),
            route_implementation_version=_ROUTE_VERSION,
            enzyme_catalog_digest=request.enzyme_catalog_digest,
        ),
        projection_inventory=(),
        claim_boundary=NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.NOT_RESOLVED,
        ),
    )
    return BasalNeighborhoodDiscoveryResult.create(discovery=discovery, realizations=exact)


__all__ = ["discover_basal_neighborhood"]
