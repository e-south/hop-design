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
from collections.abc import Iterator
from importlib.metadata import version
from itertools import product

from hop_design.kernel.construction.basal import (
    BasalPlacementFailure,
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
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    SearchCompletionStatus,
    SearchDisposition,
    SearchFeasibilityStatus,
    SearchStopMode,
    SearchTerminationReason,
    problem_id,
)
from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
    BasalRealizationRecord,
)
from hop_design.models.junction import Strand
from hop_design.models.sequence import iupac_bases

from ..sequence_domain import partition_payload_accounting, partition_sequence_domain
from .reactions import _ROUTE_VERSION
from .realization import _groups, _realization

_BASES = ("A", "C", "G", "T")


def _payload_assignments(request: LocalNeighborhoodRequest) -> Iterator[str]:
    domains = tuple(
        tuple(base for base in _BASES if base in iupac_bases(symbol))
        for symbol in request.payload.payload.sequence
    )
    for assignment in product(*domains):
        yield "".join(assignment)


def _payload_cardinality(request: LocalNeighborhoodRequest) -> int:
    cardinality = 1
    for symbol in request.payload.payload.sequence:
        cardinality *= len(iupac_bases(symbol))
    return cardinality


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

    payload_total = _payload_cardinality(request)
    records: list[BasalRealizationRecord] = []
    levels: list[OverheadLevelSummary] = []
    failures: Counter[str] = Counter()
    compatible_payloads: set[str] = set()
    payload_failures: dict[str, set[str]] = defaultdict(set)
    examined = 0
    rejected = 0
    termination: SearchTerminationReason | None = None
    exact_targets = request.geometry_domain.exact_targets()
    target_overhead = 2 * len(request.geometry_domain.pairing_constraints)

    for retained_overhead_nt in range(request.search.max_retained_overhead_nt + 1):
        level_ids: list[str] = []
        level_failures: Counter[str] = Counter()
        level_rejected = 0
        targets = exact_targets if retained_overhead_nt == target_overhead else ()
        for target in targets:
            for exact_target in _exact_strand_targets(target):
                routes = iter_basal_programs(
                    request.enzyme_provisioning,
                    target=exact_target,
                    endpoint=request.endpoint,
                )
                for payload_sequence in _payload_assignments(request):
                    for route in routes:
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
    accounting = _payload_accounting(
        request=request,
        records=exact,
        compatible_payloads=compatible_payloads,
        payload_failures=payload_failures,
        payload_total=payload_total,
        partition_accounting=partition_accounting,
        incomplete=termination is not None,
    )
    if (
        termination is None
        and exact
        and request.hard_constraints.require_all_members_compatible
        and accounting.excluded_assignments
    ):
        exact, levels, rejected, failures = _reject_partial_payload_routes(
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
        disposition=_disposition(termination=termination, has_results=bool(exact)),
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


def _disposition(
    *, termination: SearchTerminationReason | None, has_results: bool
) -> SearchDisposition:
    if termination is None:
        return SearchDisposition(
            completion=SearchCompletionStatus.COMPLETE,
            feasibility=(
                SearchFeasibilityStatus.FEASIBLE
                if has_results
                else SearchFeasibilityStatus.INFEASIBLE
            ),
            termination_reason=SearchTerminationReason.EXHAUSTED_DOMAIN,
        )
    if termination is SearchTerminationReason.RESULT_QUOTA:
        return SearchDisposition(
            completion=SearchCompletionStatus.STOPPED_BY_POLICY,
            feasibility=SearchFeasibilityStatus.FEASIBLE,
            termination_reason=termination,
        )
    return SearchDisposition(
        completion=SearchCompletionStatus.TRUNCATED,
        feasibility=(
            SearchFeasibilityStatus.FEASIBLE
            if has_results
            else SearchFeasibilityStatus.UNKNOWN
        ),
        termination_reason=termination,
    )


def _payload_accounting(
    *,
    request: LocalNeighborhoodRequest,
    records: tuple[BasalRealizationRecord, ...],
    compatible_payloads: set[str],
    payload_failures: dict[str, set[str]],
    payload_total: int,
    partition_accounting: PayloadCompatibilityAccounting | None,
    incomplete: bool,
) -> PayloadCompatibilityAccounting:
    if incomplete:
        return PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.NOT_COMPUTED,
            total_assignments=payload_total,
            exhaustive=False,
            warning="Bounded basal discovery did not exhaust route compatibility.",
        )
    if partition_accounting is not None:
        return partition_accounting
    if records:
        excluded = payload_total - len(compatible_payloads)
        conflicts = Counter(
            code
            for payload, codes in payload_failures.items()
            if payload not in compatible_payloads
            for code in codes
        )
        return PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.COMPLETE,
            total_assignments=payload_total,
            compatible_assignments=len(compatible_payloads),
            excluded_assignments=excluded,
            conflict_counts=tuple(
                FailureReasonCount(code=code, count=count)
                for code, count in sorted(conflicts.items())
                if count <= excluded
            ),
            exhaustive=True,
        )
    payload_conflicts = Counter(
        (
            "payload-recognition-conflict"
            if "recognition-payload-conflict" in payload_failures[payload]
            else "payload-no-basal-realization"
        )
        for payload in _payload_assignments(request)
    )
    return PayloadCompatibilityAccounting(
        status=PayloadCompatibilityStatus.COMPLETE,
        total_assignments=payload_total,
        compatible_assignments=0,
        excluded_assignments=payload_total,
        conflict_counts=tuple(
            FailureReasonCount(code=code, count=count)
            for code, count in sorted(payload_conflicts.items())
        ),
        exhaustive=True,
    )


def _reject_partial_payload_routes(
    *,
    records: tuple[BasalRealizationRecord, ...],
    levels: list[OverheadLevelSummary],
    rejected_count: int,
    failures: Counter[str],
) -> tuple[tuple[BasalRealizationRecord, ...], list[OverheadLevelSummary], int, Counter[str]]:
    code = "all-members-compatibility-required"
    failures[code] += len(records)
    updated: list[OverheadLevelSummary] = []
    for level in levels:
        level_failures = Counter(
            {reason.code: reason.count for reason in level.failure_reasons}
        )
        if level.realization_ids:
            level_failures[code] += len(level.realization_ids)
        updated.append(
            OverheadLevelSummary(
                retained_overhead_nt=level.retained_overhead_nt,
                examined=level.examined,
                complete=level.complete,
                candidate_count=level.candidate_count,
                realization_ids=(),
                rejected_count=level.rejected_count + len(level.realization_ids),
                failure_reasons=tuple(
                    FailureReasonCount(code=reason, count=count)
                    for reason, count in sorted(level_failures.items())
                ),
            )
        )
    return (), updated, rejected_count + len(records), failures


__all__ = ["discover_basal_neighborhood"]
