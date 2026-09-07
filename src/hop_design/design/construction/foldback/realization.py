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

from hop_design.kernel.construction.foldback import (
    FoldbackProgramCandidate,
    FoldbackSequenceSolution,
)
from hop_design.models.construction import (
    FoldbackTarget,
    LocalNeighborhoodRequest,
    LocalRealization,
    OverheadPosition,
    PayloadSourceMap,
    PayloadSourceSegment,
    ProjectionInventoryItem,
    ProjectionInventoryStatus,
    RealizationGroup,
    RealizationGrouping,
    RetainedOverheadLedger,
    SourceOrientation,
    geometry_id,
)
from hop_design.models.construction.foldback import (
    FoldbackCleavageProgramKind,
    FoldbackLocalRealization,
    FoldbackMaterialRequirement,
)
from hop_design.models.construction.foldback_replay import replay_foldback_route
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.physical import Strand
from hop_design.models.reaction_replay import assess_reaction_program

_ROUTE_VERSION = "linear-source-foldback/3"


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
        material_requirements = (
            FoldbackMaterialRequirement.SOURCE_BOTTOM_5PRIME_PHOSPHATE
            if target.nick_strand is Strand.TOP
            else FoldbackMaterialRequirement.SOURCE_TOP_5PRIME_PHOSPHATE,
        )
    else:
        material_requirements = ()
    stage_ids = tuple(stage.stage_id for stage in replay.reaction_program.stages)
    local = LocalRealization.create(
        local_sequence=solution.source_reference_sequence,
        enzyme_binding_ids=tuple(binding.binding_id for binding in bindings),
        stage_ids=stage_ids,
        achieved_geometry=target,
    )
    released_ids = set(replay.released_fragment_ids)
    retained_sequence = replay.ligated_strand.sequence
    overhead_start = len(payload_sequence)
    overhead_end = len(retained_sequence) - len(payload_sequence)
    retained_overhead = RetainedOverheadLedger(
        neighborhood="foldback",
        reference_state_id="foldback-local-product",
        positions=tuple(
            OverheadPosition(
                coordinate_space="foldback-path",
                position=position,
                base=retained_sequence[position],
                material_role="source",
            )
            for position in range(overhead_start, overhead_end)
        ),
        retained_overhead_nt=overhead_end - overhead_start,
    )
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
                        start=Boundary(
                            offset=(
                                0
                                if target.nick_strand is Strand.TOP
                                else len(solution.source_reference_sequence) - len(payload_sequence)
                            )
                        ),
                        end=Boundary(
                            offset=(
                                len(payload_sequence)
                                if target.nick_strand is Strand.TOP
                                else len(solution.source_reference_sequence)
                            )
                        ),
                    ),
                    orientation=(
                        SourceOrientation.FORWARD
                        if target.nick_strand is Strand.TOP
                        else SourceOrientation.REVERSE_COMPLEMENT
                    ),
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
        retained_sequence=retained_sequence,
        annealing_pairs=replay.annealing_pairs,
        ligation_bond=replay.ligation_bond,
        ligated_strand=replay.ligated_strand,
        reaction_program=replay.reaction_program,
        stage_assessments=assessment.stage_assessments,
        retained_overhead=retained_overhead,
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


def _projection_inventory(*, partitioned: bool) -> tuple[ProjectionInventoryItem, ...]:
    feasibility_schema = (
        "hop.foldback-feasibility-landscape/v4"
        if partitioned
        else "hop.foldback-feasibility-landscape/v3"
    )
    feasibility_renderer = (
        "foldback-feasibility-projections/4"
        if partitioned
        else "foldback-feasibility-projections/3"
    )
    overhead_schema = (
        "hop.foldback-overhead-frontier/v2" if partitioned else "hop.foldback-overhead-frontier/v1"
    )
    overhead_renderer = (
        "foldback-overhead-projections/2" if partitioned else "foldback-overhead-projections/1"
    )
    return (
        ProjectionInventoryItem(
            projection_schema="hop.foldback-nucleotide-exemplar/v1",
            renderer_version="foldback-projections/2",
            status=ProjectionInventoryStatus.NOT_GENERATED,
        ),
        ProjectionInventoryItem(
            projection_schema="hop.foldback-geometry-count-table/v1",
            renderer_version="foldback-projections/2",
            status=ProjectionInventoryStatus.NOT_GENERATED,
        ),
        ProjectionInventoryItem(
            projection_schema=feasibility_schema,
            renderer_version=feasibility_renderer,
            status=ProjectionInventoryStatus.NOT_GENERATED,
        ),
        ProjectionInventoryItem(
            projection_schema=overhead_schema,
            renderer_version=overhead_renderer,
            status=ProjectionInventoryStatus.NOT_GENERATED,
        ),
    )
