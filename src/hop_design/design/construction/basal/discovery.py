"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/basal/discovery.py

Discovers exact basal construction neighborhoods.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterator
from importlib.metadata import version
from itertools import product

from hop_design.design.relaxation import relaxation_shells
from hop_design.kernel.construction.basal import (
    BasalPlacementFailure,
    iter_basal_program_solutions,
    iter_basal_programs,
)
from hop_design.models.construction import (
    BasalNickStrand,
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
from hop_design.models.junction import Strand
from hop_design.models.sequence import iupac_bases

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
    if target.nick_strand is not BasalNickStrand.ANY:
        return (target,)
    return tuple(target.model_copy(update={"nick_strand": strand}) for strand in Strand)


def discover_basal_neighborhood(
    request: LocalNeighborhoodRequest,
) -> BasalNeighborhoodDiscoveryResult:
    """Return every state-valid basal realization within the declared finite search."""
    if request.family is not LocalNeighborhoodFamily.BASAL or not isinstance(
        request.target, BasalTarget
    ):
        raise ValueError("Basal discovery requires a basal-neighborhood request.")
    payload_total = _payload_cardinality(request)
    records: list[BasalRealizationRecord] = []
    shells: list[RelaxationShellSummary] = []
    failures: Counter[str] = Counter()
    compatible_payloads: set[str] = set()
    payload_failures: dict[str, set[str]] = defaultdict(set)
    examined = rejected = 0
    truncation: str | None = None
    for shell in relaxation_shells(request.target, request.relaxation):
        if examined >= request.enumeration.max_search_nodes:
            truncation = "max_search_nodes"
            break
        if len(records) >= request.enumeration.max_realizations:
            truncation = "max_realizations"
            break
        shell_ids: list[str] = []
        shell_failures: Counter[str] = Counter()
        shell_rejected = 0
        for geometry in shell.geometries:
            if not isinstance(geometry, BasalTarget):
                raise ValueError("Basal relaxation produced a non-basal geometry.")
            for exact_geometry in _exact_strand_targets(geometry):
                routes = iter_basal_programs(
                    request.enzyme_provisioning,
                    target=exact_geometry,
                    endpoint=request.endpoint,
                )
                for payload_sequence in _payload_assignments(request):
                    for route in routes:
                        for solution in iter_basal_program_solutions(
                            payload_sequence=payload_sequence,
                            target=exact_geometry,
                            endpoint=request.endpoint,
                            program=route,
                        ):
                            if examined >= request.enumeration.max_search_nodes:
                                truncation = "max_search_nodes"
                                break
                            if len(records) >= request.enumeration.max_realizations:
                                truncation = "max_realizations"
                                break
                            examined += 1
                            if isinstance(solution, BasalPlacementFailure):
                                failures[solution.code] += 1
                                shell_failures[solution.code] += 1
                                rejected += 1
                                shell_rejected += 1
                                payload_failures[payload_sequence].add(solution.code)
                                continue
                            record = _realization(
                                request=request,
                                payload_sequence=payload_sequence,
                                target=exact_geometry,
                                route=route,
                                solution=solution,
                                relaxation_radius=shell.radius,
                            )
                            if isinstance(record, str):
                                failures[record] += 1
                                shell_failures[record] += 1
                                rejected += 1
                                shell_rejected += 1
                                payload_failures[payload_sequence].add(record)
                                continue
                            records.append(record)
                            shell_ids.append(record.local_realization.local_realization_id)
                            compatible_payloads.add(payload_sequence)
                        if truncation:
                            break
                    if truncation:
                        break
                if truncation:
                    break
            if truncation:
                break
        shells.append(
            RelaxationShellSummary(
                radius=shell.radius,
                examined=True,
                complete=truncation is None,
                candidate_count=len(shell_ids) + shell_rejected,
                realization_ids=tuple(shell_ids),
                rejected_count=shell_rejected,
                failure_reasons=tuple(
                    FailureReasonCount(code=code, count=count)
                    for code, count in sorted(shell_failures.items())
                ),
            )
        )
        if truncation or (
            request.relaxation.mode is RelaxationMode.FIRST_FEASIBLE_SHELL
            and shell_ids
            and (
                not request.hard_constraints.require_all_members_compatible
                or len(compatible_payloads) == payload_total
            )
        ):
            break
    exact = tuple(records)
    if truncation:
        status = SearchCompletionStatus.TRUNCATED
        accounting = PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.NOT_COMPUTED,
            total_assignments=payload_total,
            exhaustive=False,
            warning="Bounded basal discovery did not exhaust route compatibility.",
        )
    elif exact:
        status = SearchCompletionStatus.COMPLETE
        excluded = payload_total - len(compatible_payloads)
        accounting = PayloadCompatibilityAccounting(
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
        status = SearchCompletionStatus.INFEASIBLE
        payload_conflicts = Counter(
            (
                "payload-recognition-conflict"
                if "recognition-payload-conflict" in payload_failures[payload]
                else "payload-no-basal-realization"
            )
            for payload in _payload_assignments(request)
        )
        accounting = PayloadCompatibilityAccounting(
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
        truncation is None
        and exact
        and request.hard_constraints.require_all_members_compatible
        and accounting.excluded_assignments
    ):
        failures["all-members-compatibility-required"] += len(exact)
        rejected += len(exact)
        exact = ()
        updated_shells: list[RelaxationShellSummary] = []
        for shell_summary in shells:
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
        shells = updated_shells
        status = SearchCompletionStatus.INFEASIBLE
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
    return BasalNeighborhoodDiscoveryResult.create(discovery=discovery, realizations=exact)
