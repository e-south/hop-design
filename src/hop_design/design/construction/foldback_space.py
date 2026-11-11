"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/foldback_space.py

Discovers and verifies complete compact foldback sequence populations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from itertools import product
from math import prod

from hop_design.design.runtime import creation_version
from hop_design.kernel.construction.foldback.admission import (
    admit_foldback_precursors,
    retained_sequences,
)
from hop_design.kernel.construction.foldback.domains import solve_foldback_sequence_domain
from hop_design.kernel.construction.foldback.programs import stream_foldback_programs
from hop_design.kernel.construction.foldback.solutions import FoldbackPlacementFailure
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.models.construction.foldback_space import (
    FoldbackProgramSupport,
    FoldbackSequenceCase,
    FoldbackSequenceRequest,
    FoldbackSequenceResult,
    foldback_case_id,
)
from hop_design.models.construction.sequence_sets import SequenceSet
from hop_design.models.construction.targets import FoldbackTarget, NickStrandSelection
from hop_design.models.physical import Strand
from hop_design.models.sequence import iupac_bases
from hop_design.serialization import canonical_json_bytes

from .foldback.realization import _ROUTE_VERSION
from .overhead import iter_foldback_geometries


def _targets(request: FoldbackSequenceRequest, payload_count: int) -> tuple[FoldbackTarget, ...]:
    targets: list[FoldbackTarget] = []
    for target in iter_foldback_geometries(
        request.geometry_domain, maximum=request.max_retained_overhead_nt
    ):
        strands = (
            (Strand.TOP, Strand.BOTTOM)
            if target.nick_strand is NickStrandSelection.ANY
            else (target.nick_strand,)
        )
        for strand in strands:
            if (len(targets) + 1) * payload_count > request.limits.max_cases:
                raise SequenceSetLimitError("Foldback case budget exhausted before expansion.")
            targets.append(target.model_copy(update={"nick_strand": strand}))
    return tuple(targets)


def discover_sequence_space(request: FoldbackSequenceRequest) -> FoldbackSequenceResult:
    """Evaluate every declared case and program or raise without complete authority."""
    request = FoldbackSequenceRequest.model_validate(request.model_dump())
    limits = request.limits
    payload_domains = tuple(
        tuple(base for base in "ACGT" if base in iupac_bases(symbol))
        for symbol in request.payload.payload.sequence
    )
    payload_count = prod(len(bases) for bases in payload_domains)
    targets = _targets(request, payload_count)
    cases = []
    program_count = 0
    decision_count = 0
    for target in targets:
        for bases in product(*payload_domains):
            payload = "".join(bases)
            length = target.annealing_arm_length_bp + target.loop_length_nt
            builder = SequenceSetBuilder(
                length_nt=length,
                max_nodes=limits.max_decisions,
                max_operations=limits.max_set_operations,
            )
            union = 0
            supports = []
            for program in stream_foldback_programs(request.enzyme_provisioning, target=target):
                program_count += 1
                if program_count > limits.max_programs:
                    raise SequenceSetLimitError("Foldback program budget exhausted.")
                domain = solve_foldback_sequence_domain(
                    payload_sequence=payload, target=target, program=program
                )
                if isinstance(domain, FoldbackPlacementFailure):
                    placement_count = 0
                    placement_failure = domain.code
                    sequences = SequenceSet(length_nt=length, decisions=(), root=0, cardinality=0)
                    precursors = sequences
                else:
                    placement_count = domain.cardinality
                    placement_failure = None
                    precursors = admit_foldback_precursors(
                        domain=domain,
                        target=target,
                        program_kind=program.kind,
                        policy=request.enzyme_provisioning,
                        max_nodes=limits.max_decisions,
                        max_operations=limits.max_set_operations,
                        max_site_checks=limits.max_site_checks,
                    )
                    sequences = retained_sequences(
                        precursors,
                        retained_length_nt=length,
                        max_nodes=limits.max_decisions,
                        max_operations=limits.max_set_operations,
                    )
                decision_count += len(sequences.decisions) + len(precursors.decisions)
                if decision_count > limits.max_result_decisions:
                    raise SequenceSetLimitError("Foldback result decision budget exhausted.")
                supports.append(
                    FoldbackProgramSupport(
                        kind=program.kind,
                        nick_enzyme_id=program.nick_enzyme.enzyme_id,
                        nick_orientation=program.nick_orientation,
                        terminus_enzyme_id=(
                            None
                            if program.terminus_enzyme is None
                            else program.terminus_enzyme.enzyme_id
                        ),
                        terminus_orientation=program.terminus_orientation,
                        placement_count=placement_count,
                        placement_failure=placement_failure,
                        sequences=sequences,
                        source_assignments=precursors,
                    )
                )
                union = builder.union(union, builder.import_set(sequences))
            admitted = builder.freeze(union)
            decision_count += len(admitted.decisions)
            if decision_count > limits.max_result_decisions:
                raise SequenceSetLimitError("Foldback result decision budget exhausted.")
            cases.append(
                FoldbackSequenceCase(
                    case_id=foldback_case_id(payload, target),
                    payload_sequence=payload,
                    target=target,
                    candidate_count=4**length,
                    programs=tuple(supports),
                    sequences=admitted,
                )
            )
    return FoldbackSequenceResult(
        request=request,
        hop_version=creation_version(),
        route_implementation_version=_ROUTE_VERSION,
        cases=tuple(cases),
        candidate_count=sum(case.candidate_count for case in cases),
        admitted_count=sum(case.sequences.cardinality for case in cases),
    )


def verify_sequence_space(result: FoldbackSequenceResult) -> FoldbackSequenceResult:
    """Admit only exact agreement with complete deterministic molecular discovery."""
    parsed = FoldbackSequenceResult.model_validate(result.model_dump())
    expected = discover_sequence_space(parsed.request)
    if canonical_json_bytes(parsed) != canonical_json_bytes(expected):
        raise ValueError("Foldback sequence result disagrees with deterministic discovery replay.")
    return parsed
