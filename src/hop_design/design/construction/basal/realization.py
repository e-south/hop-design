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
    BasalBoundaryControl,
    BasalEndpointProjection,
    BasalEnzymeDefinition,
    BasalMaterialAccounting,
    BasalMaterialRecord,
    BasalMaterialRole,
    BasalRealizationRecord,
)
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.coordinates import Span
from hop_design.models.enzymes import characterized_enzyme_digest
from hop_design.models.junction import Strand
from hop_design.models.reaction_replay import assess_reaction_program

from .reactions import _nick_program, _nicked_duplex
from .states import _pcr_states


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
    annealed, adapter_ligated, duplex = _pcr_states(solution)
    if annealed is None or adapter_ligated is None or duplex is None:
        raise RuntimeError("Basal discovery must materialize its exact PCR intermediate.")
    programs = [nick_program]
    assessments = list(nick_assessment.stage_assessments)
    pcr_reference = duplex.top_strand.sequence
    projection = BasalEndpointProjection(
        endpoint=request.endpoint,
        pairing_state=solution.pairing_state,
        pcr_reference_sequence=pcr_reference,
        pcr_complement_sequence=duplex.bottom_strand.sequence,
    )
    stage_ids = tuple(stage.stage_id for program in programs for stage in program.stages)
    local = LocalRealization.create(
        local_sequence=pcr_reference or solution.source_precursor_sequence,
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
    retained_sequence = pcr_reference
    transient_sequence = ""
    materials = [
        BasalMaterialRecord(
            material_id="retained-product",
            role=BasalMaterialRole.RETAINED,
            sequence_5prime=retained_sequence,
        )
    ]
    if transient_sequence:
        materials.append(
            BasalMaterialRecord(
                material_id="transient-periphery",
                role=BasalMaterialRole.TRANSIENT,
                sequence_5prime=transient_sequence,
            )
        )
    if solution.adapter_sequence:
        materials.append(
            BasalMaterialRecord(
                material_id="ligation-adapter",
                role=BasalMaterialRole.AUXILIARY,
                sequence_5prime=solution.adapter_sequence,
            )
        )
    totals = {
        role: sum(len(item.sequence_5prime) for item in materials if item.role is role)
        for role in BasalMaterialRole
    }
    payload_start = solution.payload_span.start.offset
    payload_end = solution.payload_span.end.offset
    retained_overhead = RetainedOverheadLedger(
        neighborhood="basal",
        reference_state_id="basal-pcr-local-boundary",
        positions=tuple(
            OverheadPosition(
                coordinate_space="basal-boundary",
                position=position,
                base=pcr_reference[position],
                material_role=("source" if position < payload_start else "adapter"),
            )
            for position in range(len(pcr_reference))
            if not payload_start <= position < payload_end
        ),
        retained_overhead_nt=len(pcr_reference) - len(payload_sequence),
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
        pairing_constraints=tuple(item.allowed_class for item in target.pairing_constraints),
        projection=projection,
        reaction_programs=tuple(programs),
        stage_assessments=tuple(assessments),
        nicked_duplex=nicked,
        adapter_annealed_complex=annealed,
        adapter_ligated_product=adapter_ligated,
        hairpin_pcr_duplex=duplex,
        materials=tuple(materials),
        material_accounting=BasalMaterialAccounting(
            retained_nt=totals[BasalMaterialRole.RETAINED],
            transient_nt=totals[BasalMaterialRole.TRANSIENT],
            auxiliary_nt=totals[BasalMaterialRole.AUXILIARY],
        ),
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
