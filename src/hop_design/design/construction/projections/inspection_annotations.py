"""Project exact operation bindings; no recognition scanning or new cleavage inference."""

from collections.abc import Mapping
from typing import Literal

from hop_design.models.construction.complete.clone.geometry import clone_payload_end_offsets
from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.projections.inspection_annotations import (
    InspectionBoundary,
    InspectionCut,
    InspectionInterface,
    InspectionOperation,
)
from hop_design.models.construction.projections.route_view import MolecularRouteView
from hop_design.models.construction.variants.inspection import MolecularAddress
from hop_design.models.coordinates import Boundary
from hop_design.models.molecular_state import MolecularStrand
from hop_design.models.reactions import ReactionOperation, ReactionProgram, ReactionStage

from .inspection_layout import lineage_key


def require_precursor_frame(program: ReactionProgram, stage: ReactionStage) -> None:
    """Verify the named target still uses the mapped precursor coordinate frame.

    Earlier operations may add released molecules without moving bindings on
    the unchanged duplex. Changed targets need a separate exact intermediate
    mapping; sequence alignment cannot establish one here.
    """
    first = program.states[0].molecules
    if len(first) != 1 or first[0].complement_sequence_5prime is None:
        raise ValueError("Operation annotation requires one mapped precursor duplex.")
    state = next(state for state in program.states if state.state_id == stage.pre_state_id)
    for operation in stage.operations:
        try:
            target = state.by_id(operation.molecule_id)
        except KeyError as error:
            raise ValueError(
                "Operation annotation requires an exact intermediate mapping."
            ) from error
        if target != first[0]:
            raise ValueError("Operation annotation requires an exact intermediate mapping.")


def inspection_operation_role(
    route: MolecularRouteView, operation: ReactionOperation, precursor_state_id: str
) -> str:
    """Name the exact construction nick; other cleanup cuts remain strand exposure.

    Partition programs record every actionable site as strand exposure. The local
    authorities still identify the basal and foldback nicks. Their shared payload
    coordinate maps locate those two boundaries without rescanning sequence or
    attributing all sites of an enzyme to its local construction role.
    """
    role = operation.role.value
    if (
        role != "strand_exposure"
        or precursor_state_id != route.source_preparation.product_state.state_id
    ):
        return role
    if len(route.payload_source_map.segments) != 1:
        return role
    complete = route.payload_source_map.segments[0]
    for name, authority in (
        ("foldback", route.foldback_authority),
        ("basal", route.basal_authority),
    ):
        if authority is None or len(authority.payload_source_map.segments) != 1:
            continue
        nick = getattr(authority, f"{name}_nick")
        if nick.enzyme_id != operation.enzyme_id:
            continue
        local = authority.payload_source_map.segments[0]
        strand = nick.strand.value
        if local.orientation == complete.orientation:
            offset = (
                complete.source_span.start.offset
                - local.source_span.start.offset
                + nick.boundary.offset
            )
        else:
            offset = (
                complete.source_span.end.offset
                + local.source_span.start.offset
                - nick.boundary.offset
            )
            strand = "bottom" if strand == "top" else "top"
        cut = getattr(
            operation.intended_binding, "reference_cut" if strand == "top" else "complement_cut"
        )
        if cut is not None and cut.offset == offset:
            return f"{name}_nick"
    return role


def address(state: ConstructionState, strand: str, index: int) -> MolecularAddress:
    return MolecularAddress(state_id=state.state_id, strand_id=strand, index=index)


def boundary(state: ConstructionState, strand: str, offset: int) -> InspectionBoundary:
    size = len(next(m for m in state.molecules if m.strand_id == strand).sequence)
    if not 0 <= offset <= size:
        raise ValueError("Inspection boundary falls outside its recorded strand.")
    return InspectionBoundary(
        before=address(state, strand, offset - 1) if offset else None,
        after=address(state, strand, offset) if offset < size else None,
    )


def inspection_operations(
    route: MolecularRouteView,
    state: ConstructionState,
    names: Mapping[str, str],
) -> tuple[InspectionOperation, ...]:
    programs = {p.program_id: p for p in route.construction_program.reaction_programs}
    positions: dict[tuple[str, str, int], list[MolecularAddress]] = {}
    for molecule in state.molecules:
        for base in molecule.lineage:
            positions.setdefault(lineage_key(base), []).append(
                address(state, molecule.strand_id, base.product_index)
            )
    result = []
    for transition in route.construction_program.transitions:
        mapping = transition.reaction_boundary_mapping
        if mapping is None or state.state_id not in (mapping.pre_state_id, mapping.post_state_id):
            continue
        applied = state.state_id == mapping.post_state_id
        if applied and state.phase.value != "cleaved_duplex":
            continue  # Released products no longer carry the complete recognition substrate.
        # Exact boundary mappings declare reference then complementary strands.
        if len(mapping.pre_strands) != 2:
            raise ValueError("Operation overlay requires its declared duplex boundary mapping.")
        top, bottom = mapping.pre_strands
        n = len(top.sequence)
        if len(bottom.sequence) != n:
            raise ValueError("Operation overlay requires a full precursor duplex.")
        program = programs[mapping.reaction_program_id]

        def mapped(strand: MolecularStrand, index: int) -> MolecularAddress:
            found = positions.get(lineage_key(strand.lineage[index]), [])
            if len(found) != 1:
                raise ValueError("Operation annotation has no unique recorded base correspondence.")
            return found[0]

        def cut(strand: MolecularStrand, offset: int, size: int = n) -> InspectionBoundary:
            return InspectionBoundary(
                before=mapped(strand, offset - 1) if offset else None,
                after=mapped(strand, offset) if offset < size else None,
            )

        for stage in program.stages:
            require_precursor_frame(program, stage)
            for operation in stage.operations:
                b = operation.intended_binding
                a, z = b.recognition_span.start.offset, b.recognition_span.end.offset
                cuts = []
                cuts_to_map: tuple[
                    tuple[Literal["reference", "complement"], MolecularStrand, Boundary | None], ...
                ] = (
                    ("reference", top, b.reference_cut),
                    ("complement", bottom, b.complement_cut),
                )
                for kind, strand, value in cuts_to_map:
                    if value is not None:
                        cuts.append(
                            InspectionCut(
                                strand=kind,
                                precursor_offset=value.offset,
                                boundary=cut(
                                    strand,
                                    value.offset if kind == "reference" else n - value.offset,
                                ),
                            )
                        )
                result.append(
                    InspectionOperation(
                        operation_id=operation.operation_id,
                        enzyme_id=operation.enzyme_id,
                        enzyme_name=names.get(operation.enzyme_id, operation.enzyme_id),
                        role=inspection_operation_role(route, operation, mapping.pre_state_id),
                        precursor_state_id=mapping.pre_state_id,
                        timing="applied" if applied else "planned",
                        orientation=b.orientation.value,
                        recognition_start=a,
                        recognition_end=z,
                        recognition=tuple(mapped(top, i) for i in range(a, z))
                        + tuple(mapped(bottom, n - 1 - i) for i in range(a, z)),
                        cuts=tuple(cuts),
                    )
                )
    return tuple(result)


def inspection_interfaces(
    route: MolecularRouteView, state: ConstructionState
) -> tuple[InspectionInterface, ...]:
    product = route.final_product
    if (
        state.state_id != route.construction_program.states[-1].state_id
        or len(product.cohesive_ends) != 2
    ):
        return ()
    left, right = product.cohesive_ends
    encoding_start = product.design_projection.source_span.start.offset
    stem_left, stem_right = (encoding_start + b for b in route.design.payload_boundaries)
    distances = clone_payload_end_offsets(
        ends=(left, right),
        encoding_start=encoding_start,
        payload_boundaries=route.design.payload_boundaries,
    )
    primary = product.strands[0]
    origin = left.primary_cut.offset
    spans = (
        (max(left.primary_cut.offset, left.complementary_cut.offset), stem_left),
        (stem_right, min(right.primary_cut.offset, right.complementary_cut.offset)),
    )
    result = []
    for end, distance, (a, z) in zip((left, right), distances, spans, strict=True):
        strand = next(m for m in state.molecules if m.strand_id == end.protruding_strand_id)
        start = (
            0
            if end.overhang_end.value == "five_prime"
            else len(strand.sequence) - len(end.sequence)
        )
        result.append(
            InspectionInterface(
                side=end.product_end,
                sequence=end.sequence,
                polarity=end.overhang_end.value,
                distance_bp=distance,
                paired_start=boundary(state, primary.strand_id, a - origin),
                paired_end=boundary(state, primary.strand_id, z - origin),
                overhang=tuple(
                    address(state, strand.strand_id, i)
                    for i in range(start, start + len(end.sequence))
                ),
            )
        )
    return tuple(result)
