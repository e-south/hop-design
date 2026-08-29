"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/foldback/realization.py

Discovers exact foldback construction neighborhoods.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from itertools import product

from hop_design.kernel.construction.foldback import (
    FoldbackProgramCandidate,
    FoldbackSequenceSolution,
)
from hop_design.models.construction import (
    FoldbackTarget,
    LocalNeighborhoodRequest,
    LocalRealization,
    PayloadSourceMap,
    PayloadSourceSegment,
    ProjectionInventoryItem,
    ProjectionInventoryStatus,
    RealizationGroup,
    RealizationGrouping,
    SourceOrientation,
    geometry_coordinate_value,
    geometry_id,
)
from hop_design.models.construction.foldback import (
    FoldbackCleavageProgramKind,
    FoldbackLocalRealization,
    FoldbackMaterialRequirement,
)
from hop_design.models.construction.foldback_replay import replay_foldback_route
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.reaction_replay import assess_reaction_program
from hop_design.models.sequence import iupac_bases

_BASES = ("A", "C", "G", "T")
_ROUTE_VERSION = "linear-source-foldback/1"


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


def _failure_code(diagnostic_codes: tuple[str, ...]) -> str:
    if "HOP-STAGE-004" in diagnostic_codes:
        return "unintended-actionable-site"
    if "HOP-PROGRAM-001" in diagnostic_codes:
        return "operation-limit"
    if "HOP-STAGE-003" in diagnostic_codes:
        return "intended-site-not-actionable"
    return "reaction-program-conflict"


def _realization(
    *,
    request: LocalNeighborhoodRequest,
    payload_sequence: str,
    target: FoldbackTarget,
    route: FoldbackProgramCandidate,
    solution: FoldbackSequenceSolution,
    relaxation_radius: int,
) -> FoldbackLocalRealization | str:
    replay = replay_foldback_route(
        payload_sequence=payload_sequence,
        target=target,
        program_kind=route.kind,
        source_reference_sequence=solution.source_reference_sequence,
        enzyme_bindings=solution.enzyme_bindings,
    )
    assessment = assess_reaction_program(
        program=replay.reaction_program,
        policy=request.enzyme_provisioning,
    )
    if assessment.report.has_errors:
        return _failure_code(tuple(diagnostic.code for diagnostic in assessment.report.diagnostics))
    bindings = solution.enzyme_bindings
    material_requirements: tuple[FoldbackMaterialRequirement, ...]
    if route.kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE:
        material_requirements = (FoldbackMaterialRequirement.SOURCE_BOTTOM_5PRIME_PHOSPHATE,)
    else:
        material_requirements = ()
    stage_ids = tuple(stage.stage_id for stage in replay.reaction_program.stages)
    local = LocalRealization.create(
        local_sequence=solution.source_reference_sequence,
        enzyme_binding_ids=tuple(binding.binding_id for binding in bindings),
        stage_ids=stage_ids,
        achieved_geometry=target,
    )
    arm_nt = target.annealing_arm_length_bp
    changed_coordinates = tuple(
        name
        for name in (
            "junction_offset_nt",
            "loop_length_nt",
            "annealing_arm_length_bp",
        )
        if geometry_coordinate_value(target, name)
        != geometry_coordinate_value(request.target, name)
    )
    released_ids = set(replay.released_fragment_ids)
    return FoldbackLocalRealization.create(
        local_realization=local,
        payload_spec_id=request.payload.payload_spec_id,
        program_kind=route.kind,
        payload_sequence=payload_sequence,
        source_reference_sequence=solution.source_reference_sequence,
        payload_source_map=PayloadSourceMap(
            segments=(
                PayloadSourceSegment(
                    payload_span=Span(
                        start=request.payload.basal_boundary,
                        end=request.payload.foldback_boundary,
                    ),
                    source_material_id="linear-source",
                    source_span=Span(
                        start=Boundary(offset=0),
                        end=Boundary(offset=len(payload_sequence)),
                    ),
                    orientation=SourceOrientation.FORWARD,
                ),
            )
        ),
        source_top_strand=replay.source_top_strand,
        source_bottom_strand=replay.source_bottom_strand,
        material_requirements=material_requirements,
        enzyme_bindings=bindings,
        foldback_nick=replay.foldback_nick,
        terminus=replay.terminus,
        molecular_fragments=replay.molecular_fragments,
        released_fragment_ids=replay.released_fragment_ids,
        released_state=replay.released_state,
        loop_sequence=replay.loop_sequence,
        foldback_arm_sequence=replay.foldback_arm_sequence,
        retained_sequence=replay.ligated_strand.sequence,
        annealing_pairs=replay.annealing_pairs,
        ligation_bond=replay.ligation_bond,
        ligated_strand=replay.ligated_strand,
        reaction_program=replay.reaction_program,
        stage_assessments=assessment.stage_assessments,
        relaxation_radius=relaxation_radius,
        changed_coordinates=changed_coordinates,
        retained_construction_nt=(target.junction_offset_nt + target.loop_length_nt + 2 * arm_nt),
        transient_construction_nt=(
            sum(
                fragment.precursor_span.length.value
                for fragment in replay.molecular_fragments
                if fragment.fragment_id in released_ids
            )
        ),
    )


def _geometry_groups(
    records: tuple[FoldbackLocalRealization, ...],
) -> tuple[RealizationGroup, ...]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for record in records:
        grouped[geometry_id(record.local_realization.achieved_geometry)].append(
            record.local_realization.local_realization_id
        )
    return tuple(
        RealizationGroup(
            grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
            group_key=group_key,
            realization_ids=tuple(realization_ids),
            multiplicity=len(realization_ids),
        )
        for group_key, realization_ids in sorted(grouped.items())
    )


def _projection_inventory() -> tuple[ProjectionInventoryItem, ...]:
    return tuple(
        ProjectionInventoryItem(
            projection_schema=schema,
            renderer_version="foldback-projections/1",
            status=ProjectionInventoryStatus.NOT_GENERATED,
        )
        for schema in (
            "hop.foldback-nucleotide-exemplar/v1",
            "hop.foldback-geometry-count-table/v1",
            "hop.foldback-feasibility-landscape/v1",
            "hop.foldback-relaxation-frontier/v1",
        )
    )
