"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/basal/discovery.py

Discovers exact basal construction neighborhoods.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from importlib.metadata import version

from hop_design.design.relaxation import relaxation_shells
from hop_design.kernel.construction.basal import (
    BasalPlacementFailure,
    iter_basal_program_solutions,
    iter_basal_programs,
)
from hop_design.models.construction import (
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
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    RelaxationMode,
    RelaxationShellSummary,
    SearchCompletionStatus,
    problem_id,
)
from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
    BasalRealizationRecord,
)
from hop_design.models.payload import ExactPayload

from .reactions import _ROUTE_VERSION
from .realization import _groups, _realization


def discover_basal_neighborhood(
    request: LocalNeighborhoodRequest,
) -> BasalNeighborhoodDiscoveryResult:
    """Return every state-valid basal realization within the declared finite search."""
    if request.family is not LocalNeighborhoodFamily.BASAL or not isinstance(
        request.target, BasalTarget
    ):
        raise ValueError("Basal discovery requires a basal-neighborhood request.")
    if not isinstance(request.payload.payload, ExactPayload):
        raise ValueError("Basal construction discovery requires an exact payload.")
    routes = iter_basal_programs(
        request.enzyme_provisioning, target=request.target, endpoint=request.endpoint
    )
    records: list[BasalRealizationRecord] = []
    shells: list[RelaxationShellSummary] = []
    failures: Counter[str] = Counter()
    examined = rejected = 0
    truncation: str | None = None
    for shell in relaxation_shells(request.target, request.relaxation):
        shell_ids: list[str] = []
        for geometry in shell.geometries:
            if not isinstance(geometry, BasalTarget):
                raise ValueError("Basal relaxation produced a non-basal geometry.")
            for route in routes:
                for solution in iter_basal_program_solutions(
                    payload_sequence=request.payload.payload.sequence,
                    target=geometry,
                    endpoint=request.endpoint,
                    program=route,
                ):
                    if examined >= request.enumeration.max_search_nodes:
                        truncation = "max_search_nodes"
                        break
                    examined += 1
                    if isinstance(solution, BasalPlacementFailure):
                        failures[solution.code] += 1
                        rejected += 1
                        continue
                    record = _realization(
                        request=request,
                        target=geometry,
                        route=route,
                        solution=solution,
                        relaxation_radius=shell.radius,
                    )
                    if isinstance(record, str):
                        failures[record] += 1
                        rejected += 1
                        continue
                    if len(records) >= request.enumeration.max_realizations:
                        truncation = "max_realizations"
                        break
                    records.append(record)
                    shell_ids.append(record.local_realization.local_realization_id)
                if truncation:
                    break
            if truncation:
                break
        shells.append(
            RelaxationShellSummary(
                radius=shell.radius, examined=True, realization_ids=tuple(shell_ids)
            )
        )
        if truncation or (
            request.relaxation.mode is RelaxationMode.FIRST_FEASIBLE_SHELL and shell_ids
        ):
            break
    exact = tuple(records)
    if truncation:
        status = SearchCompletionStatus.TRUNCATED
        accounting = PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.NOT_COMPUTED,
            total_assignments=1,
            exhaustive=False,
            warning="Bounded basal discovery did not exhaust route compatibility.",
        )
    elif exact:
        status = SearchCompletionStatus.COMPLETE
        accounting = PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.COMPLETE,
            total_assignments=1,
            compatible_assignments=1,
            excluded_assignments=0,
            exhaustive=True,
        )
    else:
        status = SearchCompletionStatus.INFEASIBLE
        accounting = PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.COMPLETE,
            total_assignments=1,
            compatible_assignments=0,
            excluded_assignments=1,
            exhaustive=True,
        )
    execution = ConstructionExecution(
        problem_id=problem_id(request),
        hop_version=version("hop-design"),
        route_implementation_version=_ROUTE_VERSION,
        enumeration=request.enumeration,
        max_operations=request.enzyme_provisioning.max_operations,
        environment={},
    )
    discovery = NeighborhoodDiscoveryResult(
        status=status,
        request=request,
        problem_id=problem_id(request),
        execution_id=execution.execution_id,
        shells=tuple(shells),
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
        truncation_reasons=((truncation,) if truncation else ()),
    )
    return BasalNeighborhoodDiscoveryResult(discovery=discovery, realizations=exact)
