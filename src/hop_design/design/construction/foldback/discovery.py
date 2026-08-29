"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/foldback/discovery.py

Discovers exact foldback construction neighborhoods.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter, defaultdict
from importlib.metadata import version

from hop_design.design.relaxation import relaxation_shells
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
    FoldbackTarget,
    LocalNeighborhoodFamily,
    LocalNeighborhoodRequest,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
    NeighborhoodDiscoveryResult,
    NeighborhoodProvenance,
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    RelaxationMode,
    RelaxationShellSummary,
    SearchCompletionStatus,
    problem_id,
)
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackNeighborhoodDiscoveryResult,
)

from .realization import (
    _ROUTE_VERSION,
    _geometry_groups,
    _payload_assignments,
    _payload_cardinality,
    _projection_inventory,
    _realization,
)


def discover_foldback_neighborhood(
    request: LocalNeighborhoodRequest,
) -> FoldbackNeighborhoodDiscoveryResult:
    """Return every state-valid foldback realization within the declared finite search."""
    if request.family is not LocalNeighborhoodFamily.FOLDBACK or not isinstance(
        request.target, FoldbackTarget
    ):
        raise ValueError("Foldback discovery requires a foldback-neighborhood request.")
    if request.endpoint is not ConstructionEndpoint.SSDNA_HAIRPIN:
        raise ValueError("Foldback-local discovery currently resolves the ssDNA hairpin endpoint.")

    routes = iter_foldback_programs(request.enzyme_provisioning)
    payload_total = _payload_cardinality(request)
    records: list[FoldbackLocalRealization] = []
    shell_summaries: list[RelaxationShellSummary] = []
    failures: Counter[str] = Counter()
    examined_nodes = 0
    rejected_count = 0
    truncation_reason: str | None = None
    compatible_payloads: set[str] = set()
    payload_failures: dict[str, set[str]] = defaultdict(set)

    for shell in relaxation_shells(request.target, request.relaxation):
        if examined_nodes >= request.enumeration.max_search_nodes:
            truncation_reason = "max_search_nodes"
            break
        if len(records) >= request.enumeration.max_realizations:
            truncation_reason = "max_realizations"
            break
        shell_ids: list[str] = []
        shell_failures: Counter[str] = Counter()
        shell_rejected = 0
        for geometry in shell.geometries:
            if not isinstance(geometry, FoldbackTarget):
                raise ValueError("Foldback relaxation produced a non-foldback geometry.")
            for payload_sequence in _payload_assignments(request):
                for route in routes:
                    for solution in iter_foldback_program_solutions(
                        payload_sequence=payload_sequence,
                        target=geometry,
                        program=route,
                    ):
                        if examined_nodes >= request.enumeration.max_search_nodes:
                            truncation_reason = "max_search_nodes"
                            break
                        if len(records) >= request.enumeration.max_realizations:
                            truncation_reason = "max_realizations"
                            break
                        examined_nodes += 1
                        if isinstance(solution, FoldbackPlacementFailure):
                            failures[solution.code] += 1
                            shell_failures[solution.code] += 1
                            rejected_count += 1
                            shell_rejected += 1
                            payload_failures[payload_sequence].add(solution.code)
                            continue
                        record = _realization(
                            request=request,
                            payload_sequence=payload_sequence,
                            target=geometry,
                            route=route,
                            solution=solution,
                            relaxation_radius=shell.radius,
                        )
                        if isinstance(record, str):
                            failures[record] += 1
                            shell_failures[record] += 1
                            rejected_count += 1
                            shell_rejected += 1
                            payload_failures[payload_sequence].add(record)
                            continue
                        records.append(record)
                        shell_ids.append(record.local_realization.local_realization_id)
                        compatible_payloads.add(payload_sequence)
                    if truncation_reason is not None:
                        break
                if truncation_reason is not None:
                    break
            if truncation_reason is not None:
                break
        shell_summaries.append(
            RelaxationShellSummary(
                radius=shell.radius,
                examined=True,
                complete=truncation_reason is None,
                candidate_count=len(shell_ids) + shell_rejected,
                realization_ids=tuple(shell_ids),
                rejected_count=shell_rejected,
                failure_reasons=tuple(
                    FailureReasonCount(code=code, count=count)
                    for code, count in sorted(shell_failures.items())
                ),
            )
        )
        if truncation_reason is not None:
            break
        if (
            request.relaxation.mode is RelaxationMode.FIRST_FEASIBLE_SHELL
            and shell_ids
            and (
                not request.hard_constraints.require_all_members_compatible
                or len(compatible_payloads) == payload_total
            )
        ):
            break

    exact_records = tuple(records)
    if truncation_reason is not None:
        status = SearchCompletionStatus.TRUNCATED
        payload_accounting = PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.NOT_COMPUTED,
            total_assignments=payload_total,
            exhaustive=False,
            warning="Bounded foldback discovery did not exhaust route compatibility.",
        )
    elif exact_records:
        status = SearchCompletionStatus.COMPLETE
        excluded = payload_total - len(compatible_payloads)
        payload_accounting = PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.COMPLETE,
            total_assignments=payload_total,
            compatible_assignments=len(compatible_payloads),
            excluded_assignments=excluded,
            conflict_counts=tuple(
                FailureReasonCount(code=code, count=count)
                for code, count in sorted(
                    Counter(
                        code
                        for payload, codes in payload_failures.items()
                        if payload not in compatible_payloads
                        for code in codes
                    ).items()
                )
                if count <= excluded
            ),
            exhaustive=True,
        )
    else:
        payload_conflicts = Counter(
            (
                "payload-recognition-conflict"
                if "payload-recognition-conflict" in payload_failures[payload]
                else "payload-no-foldback-realization"
            )
            for payload in _payload_assignments(request)
        )
        status = SearchCompletionStatus.INFEASIBLE
        payload_accounting = PayloadCompatibilityAccounting(
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

    if (
        truncation_reason is None
        and exact_records
        and request.hard_constraints.require_all_members_compatible
        and payload_accounting.excluded_assignments
    ):
        failures["all-members-compatibility-required"] += len(exact_records)
        rejected_count += len(exact_records)
        exact_records = ()
        updated_shells: list[RelaxationShellSummary] = []
        for shell_summary in shell_summaries:
            shell_failures = Counter(
                {reason.code: reason.count for reason in shell_summary.failure_reasons}
            )
            shell_failures["all-members-compatibility-required"] += len(
                shell_summary.realization_ids
            )
            updated_shells.append(
                RelaxationShellSummary(
                    radius=shell_summary.radius,
                    examined=shell_summary.examined,
                    complete=shell_summary.complete,
                    candidate_count=shell_summary.candidate_count,
                    realization_ids=(),
                    rejected_count=shell_summary.rejected_count
                    + len(shell_summary.realization_ids),
                    failure_reasons=tuple(
                        FailureReasonCount(code=code, count=count)
                        for code, count in sorted(shell_failures.items())
                    ),
                )
            )
        shell_summaries = updated_shells
        status = SearchCompletionStatus.INFEASIBLE

    hop_version = version("hop-design")
    execution = ConstructionExecution(
        problem_id=problem_id(request),
        hop_version=hop_version,
        route_implementation_version=_ROUTE_VERSION,
        enumeration=request.enumeration,
        max_operations=request.enzyme_provisioning.max_operations,
        environment={},
    )
    neighborhood = NeighborhoodDiscoveryResult(
        status=status,
        request=request,
        problem_id=problem_id(request),
        execution_id=execution.execution_id,
        execution=execution,
        shells=tuple(shell_summaries),
        realizations=tuple(record.local_realization for record in exact_records),
        achieved_geometry_groups=_geometry_groups(exact_records),
        rejected_count=rejected_count,
        failure_reasons=tuple(
            FailureReasonCount(code=code, count=count) for code, count in sorted(failures.items())
        ),
        payload_compatibility=payload_accounting,
        provenance=NeighborhoodProvenance(
            hop_version=hop_version,
            route_implementation_version=_ROUTE_VERSION,
            enzyme_catalog_digest=request.enzyme_catalog_digest,
        ),
        projection_inventory=_projection_inventory(),
        claim_boundary=NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.NOT_RESOLVED,
        ),
        truncation_reasons=((truncation_reason,) if truncation_reason else ()),
    )
    return FoldbackNeighborhoodDiscoveryResult(
        neighborhood=neighborhood,
        realizations=exact_records,
    )
