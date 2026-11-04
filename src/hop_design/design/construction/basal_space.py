"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/basal_space.py

Discovers and verifies complete canonical basal sequence populations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from importlib.metadata import version
from itertools import product
from math import prod

from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain
from hop_design.kernel.construction.basal.programs import (
    BasalPlacementFailure,
    stream_basal_programs,
)
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.models.construction.basal_space import (
    BasalProgramSupport,
    BasalSequenceCase,
    BasalSequenceRequest,
    BasalSequenceResult,
    basal_case_id,
)
from hop_design.models.construction.search import BasalGeometryDomain
from hop_design.models.construction.sequence_sets import SequenceSet
from hop_design.models.construction.targets import NickStrandSelection
from hop_design.models.physical import Strand
from hop_design.models.sequence import iupac_bases
from hop_design.serialization import canonical_json_bytes

from .basal.reactions import _ROUTE_VERSION
from .basal_space_admission import admit_basal_sources


def _geometries(
    request: BasalSequenceRequest, payload_count: int
) -> tuple[BasalGeometryDomain, ...]:
    geometries: list[BasalGeometryDomain] = []
    geometry = request.geometry_domain
    strands = (
        tuple(Strand)
        if geometry.nick_strand is NickStrandSelection.ANY
        else (geometry.nick_strand,)
    )
    for nick in geometry.nick_offsets_nt:
        if nick + len(geometry.pairing_constraints) > request.max_retained_overhead_nt:
            continue
        for strand in strands:
            if (len(geometries) + 1) * payload_count > request.limits.max_cases:
                raise SequenceSetLimitError("Basal case budget exhausted before expansion.")
            geometries.append(
                geometry.model_copy(update={"nick_offsets_nt": (nick,), "nick_strand": strand})
            )
    return tuple(geometries)


def discover_sequence_space(request: BasalSequenceRequest) -> BasalSequenceResult:
    """Evaluate every declared case and program or raise without complete authority."""
    request = BasalSequenceRequest.model_validate(request.model_dump())
    limits = request.limits
    payload_domains = tuple(
        tuple(base for base in "ACGT" if base in iupac_bases(symbol))
        for symbol in request.payload.payload.sequence
    )
    geometries = _geometries(request, prod(len(bases) for bases in payload_domains))
    cases = []
    program_count = decision_count = 0
    for geometry in geometries:
        width = geometry.nick_offsets_nt[0] + len(geometry.pairing_constraints)
        for bases in product(*payload_domains):
            payload = "".join(bases)
            builder = SequenceSetBuilder(
                length_nt=width,
                max_nodes=limits.max_decisions,
                max_operations=limits.max_set_operations,
            )
            union = 0
            supports = []
            for target in geometry.exact_targets():
                for program in stream_basal_programs(
                    request.enzyme_provisioning, target=target, endpoint=request.endpoint
                ):
                    program_count += 1
                    if program_count > limits.max_programs:
                        raise SequenceSetLimitError("Basal program budget exhausted.")
                    domain = solve_basal_sequence_domain(
                        payload_sequence=payload,
                        target=target,
                        endpoint=request.endpoint,
                        program=program,
                    )
                    source = None
                    start = None
                    if isinstance(domain, BasalPlacementFailure):
                        placement_count, failure = 0, domain.code
                        sequences = SequenceSet(
                            length_nt=width, decisions=(), root=0, cardinality=0
                        )
                    else:
                        placement_count = prod(
                            len(bases) for bases in domain.canonical_source_domains()
                        )
                        failure = None
                        source = admit_basal_sources(
                            domain=domain, policy=request.enzyme_provisioning, limits=limits
                        )
                        start = domain.payload_span.start.offset - width
                        projection = SequenceSetBuilder(
                            length_nt=width,
                            max_nodes=limits.max_decisions,
                            max_operations=limits.max_set_operations,
                        )
                        sequences = projection.freeze(
                            projection.project_window(source, start=start, end=start + width)
                        )
                    decision_count += len(sequences.decisions) + (
                        len(source.decisions) if source is not None else 0
                    )
                    if decision_count > limits.max_result_decisions:
                        raise SequenceSetLimitError("Basal result decision budget exhausted.")
                    supports.append(
                        BasalProgramSupport(
                            target=target,
                            nick_enzyme_id=program.nick_enzyme.enzyme_id,
                            nick_orientation=program.nick_orientation,
                            future_release_enzyme_id=program.future_release_enzyme.enzyme_id
                            if program.future_release_enzyme is not None
                            else None,
                            placement_failure=failure,
                            placement_count=placement_count,
                            source_window_start=start,
                            source_sequences=source,
                            sequences=sequences,
                        )
                    )
                    union = builder.union(union, builder.import_set(sequences))
            admitted = builder.freeze(union)
            decision_count += len(admitted.decisions)
            if decision_count > limits.max_result_decisions:
                raise SequenceSetLimitError("Basal result decision budget exhausted.")
            cases.append(
                BasalSequenceCase(
                    case_id=basal_case_id(payload, request.endpoint, geometry),
                    payload_sequence=payload,
                    endpoint=request.endpoint,
                    geometry=geometry,
                    candidate_count=4**width,
                    programs=tuple(supports),
                    sequences=admitted,
                )
            )
    return BasalSequenceResult(
        request=request,
        hop_version=version("hop-design"),
        route_implementation_version=_ROUTE_VERSION,
        cases=tuple(cases),
        candidate_count=sum(c.candidate_count for c in cases),
        admitted_count=sum(c.sequences.cardinality for c in cases),
    )


def verify_sequence_space(result: BasalSequenceResult) -> BasalSequenceResult:
    """Accept only exact agreement with complete deterministic molecular rediscovery."""
    parsed = BasalSequenceResult.model_validate(result.model_dump())
    expected = discover_sequence_space(parsed.request)
    if canonical_json_bytes(parsed) != canonical_json_bytes(expected):
        raise ValueError("Basal sequence result disagrees with deterministic discovery replay.")
    return parsed
