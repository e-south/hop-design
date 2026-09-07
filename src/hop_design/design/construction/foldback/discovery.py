"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/foldback/discovery.py

Discovers exact foldback constructions in retained-overhead order.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter, defaultdict
from importlib.metadata import version

from hop_design.design.construction.overhead import foldback_overhead_levels
from hop_design.kernel.construction.foldback import (
    FoldbackPlacementFailure,
    iter_foldback_program_solutions,
    iter_foldback_programs,
)
from hop_design.models.construction import (
    ConstructionEndpoint,
    ConstructionExecution,
    DigitalDesignStatus,
    FailureReasonCount,
    FoldbackGeometryDomain,
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
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackNeighborhoodDiscoveryResult,
)
from hop_design.models.physical import Strand

from ..neighborhood_accounting import (
    payload_accounting,
    payload_assignments,
    payload_cardinality,
    reject_partial_payload_routes,
    search_disposition,
)
from ..sequence_domain import partition_payload_accounting, partition_sequence_domain
from .realization import (
    _ROUTE_VERSION,
    _geometry_groups,
    _projection_inventory,
    _realization,
)


def discover_foldback_neighborhood(
    request: LocalNeighborhoodRequest,
) -> FoldbackNeighborhoodDiscoveryResult:
    """Return exact foldback realizations across the finite overhead domain."""
    if request.family is not LocalNeighborhoodFamily.FOLDBACK or not isinstance(
        request.geometry_domain, FoldbackGeometryDomain
    ):
        raise ValueError("Foldback discovery requires a foldback geometry domain.")
    if request.endpoint is not ConstructionEndpoint.SSDNA_HAIRPIN:
        raise ValueError("Foldback-local discovery resolves the ssDNA hairpin endpoint.")

    payload_total = payload_cardinality(request)
    records: list[FoldbackLocalRealization] = []
    level_summaries: list[OverheadLevelSummary] = []
    failures: Counter[str] = Counter()
    examined_nodes = 0
    rejected_count = 0
    termination: SearchTerminationReason | None = None
    compatible_payloads: set[str] = set()
    payload_failures: dict[str, set[str]] = defaultdict(set)

    for level in foldback_overhead_levels(request.geometry_domain, request.search):
        level_ids: list[str] = []
        level_failures: Counter[str] = Counter()
        level_rejected = 0
        for geometry in level.geometries:
            exact_geometries = (
                tuple(geometry.model_copy(update={"nick_strand": strand}) for strand in Strand)
                if geometry.nick_strand is NickStrandSelection.ANY
                else (geometry,)
            )
            for exact_geometry in exact_geometries:
                routes = iter_foldback_programs(
                    request.enzyme_provisioning,
                    target=exact_geometry,
                )
                for payload_sequence in payload_assignments(request):
                    for route in routes:
                        solutions = partition_sequence_domain(
                            iter_foldback_program_solutions(
                                payload_sequence=payload_sequence,
                                target=exact_geometry,
                                program=route,
                            ),
                            request.search.sequence_partition,
                        )
                        for solution in solutions:
                            if examined_nodes >= request.search.max_search_nodes:
                                termination = SearchTerminationReason.EVALUATION_CAP
                                break
                            examined_nodes += 1
                            if isinstance(solution, FoldbackPlacementFailure):
                                failures[solution.code] += 1
                                level_failures[solution.code] += 1
                                rejected_count += 1
                                level_rejected += 1
                                payload_failures[payload_sequence].add(solution.code)
                                continue
                            record = _realization(
                                request=request,
                                payload_sequence=payload_sequence,
                                target=exact_geometry,
                                route=route,
                                solution=solution,
                            )
                            if isinstance(record, str):
                                failures[record] += 1
                                level_failures[record] += 1
                                rejected_count += 1
                                level_rejected += 1
                                payload_failures[payload_sequence].add(record)
                                continue
                            if len(records) >= request.search.max_realizations:
                                termination = SearchTerminationReason.EVALUATION_CAP
                                break
                            if (
                                record.retained_overhead.retained_overhead_nt
                                != level.retained_overhead_nt
                            ):
                                raise RuntimeError(
                                    "Foldback geometry and endpoint overhead ledger disagree."
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
        level_summaries.append(
            OverheadLevelSummary(
                retained_overhead_nt=level.retained_overhead_nt,
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

    exact_records = tuple(records)
    partition_accounting = partition_payload_accounting(
        request.search.sequence_partition,
        total_assignments=payload_total,
    )
    payload_accounting_result = payload_accounting(
        request=request,
        has_records=bool(exact_records),
        compatible_payloads=compatible_payloads,
        payload_failures=payload_failures,
        payload_total=payload_total,
        partition_accounting=partition_accounting,
        incomplete=termination is not None,
        incomplete_warning="Bounded foldback discovery did not exhaust route compatibility.",
        recognition_failure_code="payload-recognition-conflict",
        recognition_conflict_code="payload-recognition-conflict",
        no_realization_code="payload-no-foldback-realization",
    )
    if (
        termination is None
        and exact_records
        and request.hard_constraints.require_all_members_compatible
        and payload_accounting_result.excluded_assignments
    ):
        exact_records, level_summaries, rejected_count, failures = reject_partial_payload_routes(
            records=exact_records,
            levels=level_summaries,
            rejected_count=rejected_count,
            failures=failures,
        )

    disposition = search_disposition(termination=termination, has_results=bool(exact_records))
    hop_version = version("hop-design")
    execution = ConstructionExecution(
        problem_id=problem_id(request),
        hop_version=hop_version,
        route_implementation_version=_ROUTE_VERSION,
        search=request.search,
        max_operations=request.enzyme_provisioning.max_operations,
        environment={},
    )
    neighborhood = NeighborhoodDiscoveryResult(
        disposition=disposition,
        request=request,
        problem_id=problem_id(request),
        execution_id=execution.execution_id,
        execution=execution,
        overhead_levels=tuple(level_summaries),
        realizations=tuple(record.local_realization for record in exact_records),
        achieved_geometry_groups=_geometry_groups(exact_records),
        rejected_count=rejected_count,
        failure_reasons=tuple(
            FailureReasonCount(code=code, count=count) for code, count in sorted(failures.items())
        ),
        payload_compatibility=payload_accounting_result,
        provenance=NeighborhoodProvenance(
            hop_version=hop_version,
            route_implementation_version=_ROUTE_VERSION,
            enzyme_catalog_digest=request.enzyme_catalog_digest,
        ),
        projection_inventory=_projection_inventory(
            partitioned=request.search.sequence_partition is not None
        ),
        claim_boundary=NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.NOT_RESOLVED,
        ),
    )
    return FoldbackNeighborhoodDiscoveryResult.create(
        neighborhood=neighborhood,
        realizations=exact_records,
    )


__all__ = ["discover_foldback_neighborhood"]
