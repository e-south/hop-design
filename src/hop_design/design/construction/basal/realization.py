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
from typing import cast

from hop_design.kernel.construction.basal import (
    BasalProgramCandidate,
    BasalSequenceSolution,
)
from hop_design.models.construction import (
    BasalTarget,
    ConstructionEndpoint,
    LocalNeighborhoodRequest,
    LocalRealization,
    PayloadSourceMap,
    PayloadSourceSegment,
    RealizationGroup,
    RealizationGrouping,
    SourceOrientation,
    geometry_coordinate_value,
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
from hop_design.models.coordinates import Span
from hop_design.models.enzymes import EnzymeRole, characterized_enzyme_digest
from hop_design.models.junction import Strand
from hop_design.models.reaction_replay import assess_reaction_program

from .reactions import _nick_program, _nicked_duplex
from .states import _end_program, _pcr_states, _restriction_product


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
    relaxation_radius: int,
) -> BasalRealizationRecord | str:
    if not isinstance(target.nick_strand, Strand):
        raise ValueError("Basal realizations require one exact nick strand.")
    required_operations = 3 if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX else 1
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
    restriction = None
    programs = [nick_program]
    assessments = list(nick_assessment.stage_assessments)
    if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        if duplex is None:
            return "pcr-state-unavailable"
        try:
            restriction = _restriction_product(solution, duplex)
        except ValueError as error:
            return str(error)
        end_program = _end_program(duplex, restriction, solution, route)
        end_assessment = assess_reaction_program(
            program=end_program, policy=request.enzyme_provisioning
        )
        if end_assessment.report.has_errors:
            return _failure_code(tuple(item.code for item in end_assessment.report.diagnostics))
        programs.append(end_program)
        assessments.extend(end_assessment.stage_assessments)
    cohesive_ends = restriction.cohesive_ends if restriction is not None else ()
    requested = (
        set(target.end_generation.requested_overhangs)
        if target.end_generation is not None
        else set()
    )
    if requested and any(end.sequence not in requested for end in cohesive_ends):
        return "requested-overhang-unavailable"
    pcr_reference = duplex.top_strand.sequence if duplex is not None else None
    projection = BasalEndpointProjection(
        endpoint=request.endpoint,
        pairing_profile=solution.pairing_profile,
        pcr_reference_sequence=pcr_reference,
        pcr_complement_sequence=duplex.bottom_strand.sequence if duplex is not None else None,
        cohesive_ends=cohesive_ends,
        asymmetric_end_encoding=len(cohesive_ends) == 2
        and (cohesive_ends[0].sequence, cohesive_ends[0].overhang_end)
        != (cohesive_ends[1].sequence, cohesive_ends[1].overhang_end),
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
    enzymes = (route.nick_enzyme,) + ((route.end_enzyme,) if route.end_enzyme is not None else ())
    definitions = tuple(
        BasalEnzymeDefinition(
            enzyme_id=enzyme.enzyme_id, digest=characterized_enzyme_digest(enzyme), enzyme=enzyme
        )
        for enzyme in enzymes
    )
    if restriction is not None:
        retained_sequence = restriction.primary_strand.sequence
        end_bindings = sorted(
            (
                binding
                for binding in solution.enzyme_bindings
                if binding.role is EnzymeRole.END_GENERATION
            ),
            key=lambda item: item.recognition_span.start.offset,
        )
        left_cut = end_bindings[0].reference_cut
        right_cut = end_bindings[1].reference_cut
        if left_cut is None or right_cut is None or pcr_reference is None:
            return "end-generation-cut-model"
        transient_sequence = pcr_reference[: left_cut.offset] + pcr_reference[right_cut.offset :]
    elif pcr_reference is not None:
        retained_sequence = pcr_reference
        transient_sequence = ""
    else:
        retained_sequence = solution.source_precursor_sequence
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
        if pcr_reference is None:
            raise RuntimeError("Adapter-bearing realization lost its PCR reference.")
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
    changed = tuple(
        name
        for name in ("nick_offset_nt", "end_generation.type_iis_cut_offset_nt")
        if _coordinate_changed(cast(BasalTarget, request.target), target, name)
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
        pairing_constraints=tuple(item.allowed_class for item in target.pairing_constraints),
        projection=projection,
        reaction_programs=tuple(programs),
        stage_assessments=tuple(assessments),
        nicked_duplex=nicked,
        adapter_annealed_complex=annealed,
        adapter_ligated_product=adapter_ligated,
        hairpin_pcr_duplex=duplex,
        restriction_digest_product=restriction,
        materials=tuple(materials),
        material_accounting=BasalMaterialAccounting(
            retained_nt=totals[BasalMaterialRole.RETAINED],
            transient_nt=totals[BasalMaterialRole.TRANSIENT],
            auxiliary_nt=totals[BasalMaterialRole.AUXILIARY],
        ),
        relaxation_radius=relaxation_radius,
        changed_coordinates=changed,
    )


def _coordinate_changed(original: BasalTarget, achieved: BasalTarget, name: str) -> bool:
    try:
        return geometry_coordinate_value(original, name) != geometry_coordinate_value(
            achieved, name
        )
    except ValueError:
        return False


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
