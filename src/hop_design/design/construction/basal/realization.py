"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/basal/realization.py

Discovers exact basal construction neighborhoods.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import defaultdict

from hop_design.kernel.construction.basal import (
    BasalProgramCandidate,
    BasalSequenceSolution,
)
from hop_design.models.construction import (
    BasalGeometryDomain,
    BasalTarget,
    LocalNeighborhoodRequest,
    LocalRealization,
    OverheadPosition,
    PayloadSourceMap,
    PayloadSourceSegment,
    RealizationGroup,
    RealizationGrouping,
    RetainedOverheadLedger,
    SourceOrientation,
    geometry_id,
)
from hop_design.models.construction.basal import (
    BasalAnnealingObligation,
    BasalBoundaryControl,
    BasalBoundaryProjection,
    BasalEnzymeDefinition,
    BasalRealizationRecord,
)
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.coordinates import Span
from hop_design.models.enzymes import characterized_enzyme_digest
from hop_design.models.junction import Strand
from hop_design.models.reaction_replay import assess_reaction_program
from hop_design.models.sequence import reverse_complement_iupac

from .reactions import _nick_program, _nicked_duplex


def _failure_code(codes: tuple[str, ...]) -> str:
    if "HOP-STAGE-004" in codes:
        return "unintended-actionable-site"
    if "HOP-PROGRAM-001" in codes:
        return "operation-limit"
    if "HOP-STAGE-003" in codes:
        return "intended-site-not-actionable"
    return "reaction-program-conflict"


def _realization(
    *,
    request: LocalNeighborhoodRequest,
    payload_sequence: str,
    target: BasalTarget,
    route: BasalProgramCandidate,
    solution: BasalSequenceSolution,
) -> BasalRealizationRecord | str:
    if request.endpoint not in {
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    }:
        raise ValueError("Basal realization requires a PCR-bearing endpoint.")
    if not isinstance(target.nick_strand, Strand):
        raise ValueError("Basal realizations require one exact nick strand.")
    if solution.pairing_state is None:
        raise ValueError("Basal realizations require one exact pairing state.")
    if not isinstance(request.geometry_domain, BasalGeometryDomain):
        raise ValueError("Basal realization requires one basal geometry domain.")
    required_operations = 1 + int(route.future_release_action is not None)
    if (
        request.enzyme_provisioning.max_operations is not None
        and required_operations > request.enzyme_provisioning.max_operations
    ):
        return "operation-limit"
    nick_program = _nick_program(solution, route)
    nick_assessment = assess_reaction_program(
        program=nick_program, policy=request.enzyme_provisioning
    )
    if nick_assessment.report.has_errors:
        return _failure_code(tuple(item.code for item in nick_assessment.report.diagnostics))
    nicked = _nicked_duplex(solution, target)
    programs = [nick_program]
    assessments = list(nick_assessment.stage_assessments)
    adapter_sequence = solution.adapter_sequence
    if adapter_sequence is None:
        raise RuntimeError("Basal discovery must resolve one proximal adapter segment.")
    local_reference = solution.source_precursor_sequence + adapter_sequence
    projection = BasalBoundaryProjection(
        endpoint=request.endpoint,
        pairing_state=solution.pairing_state,
        annealing_obligation=BasalAnnealingObligation.create(
            pairing_state=solution.pairing_state,
            minimum_annealing_nt=request.geometry_domain.minimum_adapter_annealing_nt,
            mismatch_warning_fraction=request.geometry_domain.mismatch_warning_fraction,
        ),
        local_reference_sequence=local_reference,
        local_complement_sequence=reverse_complement_iupac(local_reference),
    )
    stage_ids = tuple(stage.stage_id for program in programs for stage in program.stages)
    local = LocalRealization.create(
        local_sequence=local_reference,
        enzyme_binding_ids=tuple(binding.binding_id for binding in solution.enzyme_bindings),
        stage_ids=stage_ids,
        achieved_geometry=target,
    )
    payload = payload_sequence
    payload_map = PayloadSourceMap(
        segments=(
            PayloadSourceSegment(
                payload_span=Span(
                    start=request.payload.basal_boundary, end=request.payload.foldback_boundary
                ),
                source_material_id="source-precursor",
                source_span=solution.payload_span,
                orientation=SourceOrientation.FORWARD,
            ),
        )
    )
    nick_binding = solution.enzyme_bindings[0]
    operative = (
        nick_binding.reference_cut
        if target.nick_strand is Strand.TOP
        else nick_binding.complement_cut
    )
    if operative is None:
        return "basal-nick-cut-unavailable"
    enzymes = (route.nick_enzyme,) + (
        () if route.future_release_enzyme is None else (route.future_release_enzyme,)
    )
    definitions = tuple(
        BasalEnzymeDefinition(
            enzyme_id=enzyme.enzyme_id, digest=characterized_enzyme_digest(enzyme), enzyme=enzyme
        )
        for enzyme in enzymes
    )
    payload_start = solution.payload_span.start.offset
    payload_end = solution.payload_span.end.offset
    retained_overhead = RetainedOverheadLedger(
        neighborhood="basal",
        reference_state_id="basal-pcr-local-boundary",
        positions=tuple(
            OverheadPosition(
                coordinate_space="basal-boundary",
                position=position,
                base=local_reference[position],
                material_role=("source" if position < payload_start else "adapter"),
            )
            for position in range(len(local_reference))
            if not payload_start <= position < payload_end
        ),
        retained_overhead_nt=len(local_reference) - len(payload_sequence),
    )
    return BasalRealizationRecord.create(
        local_realization=local,
        payload_sequence=payload,
        source_precursor_sequence=solution.source_precursor_sequence,
        payload_source_map=payload_map,
        enzyme_definitions=definitions,
        enzyme_bindings=solution.enzyme_bindings,
        basal_nick=BasalBoundaryControl(
            strand=target.nick_strand,
            boundary=operative,
            enzyme_id=route.nick_enzyme.enzyme_id,
            binding_id=nick_binding.binding_id,
        ),
        future_release_action=route.future_release_action,
        pairing_constraints=target.pairing_constraints,
        projection=projection,
        reaction_programs=tuple(programs),
        stage_assessments=tuple(assessments),
        nicked_duplex=nicked,
        retained_overhead=retained_overhead,
    )


def _groups(records: tuple[BasalRealizationRecord, ...]) -> tuple[RealizationGroup, ...]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for record in records:
        grouped[geometry_id(record.local_realization.achieved_geometry)].append(
            record.local_realization.local_realization_id
        )
    return tuple(
        RealizationGroup(
            grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
            group_key=key,
            realization_ids=tuple(ids),
            multiplicity=len(ids),
        )
        for key, ids in sorted(grouped.items())
    )
