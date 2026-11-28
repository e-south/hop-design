"""Follow route-bound recognition footprints, separately from reaction activity."""

from collections import defaultdict
from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.projections.inspection_annotations import (
    InspectionRecognitionSite,
)
from hop_design.models.construction.projections.route_view import MolecularRouteView
from hop_design.models.construction.variants.inspection import MolecularAddress

from .inspection_annotations import inspection_operation_role, require_precursor_frame
from .inspection_layout import Origin
from .inspection_lineage import ancestry_resolver


class RecognitionAncestry:
    """Route-local index shared across state projections, never retained globally."""

    def __init__(self, route: MolecularRouteView):
        self.route = route
        self.resolve = ancestry_resolver(route)
        positions: list[Mapping[Origin, tuple[MolecularAddress, ...]]] = []
        for state in (route.source_preparation.input_state, *route.construction_program.states):
            mapped: dict[Origin, list[MolecularAddress]] = defaultdict(list)
            for molecule in state.molecules:
                for base in molecule.lineage:
                    mapped[self.resolve(base)].append(
                        MolecularAddress(
                            state_id=state.state_id,
                            strand_id=molecule.strand_id,
                            index=base.product_index,
                        )
                    )
            positions.append(MappingProxyType({key: tuple(value) for key, value in mapped.items()}))
        self.positions = tuple(positions)


def inspection_recognition_sites(
    route: MolecularRouteView,
    state: ConstructionState,
    names: Mapping[str, str],
    *,
    ancestry: RecognitionAncestry | None = None,
) -> tuple[InspectionRecognitionSite, ...]:
    states = (route.source_preparation.input_state, *route.construction_program.states)
    state_index = next(i for i, s in enumerate(states) if s.state_id == state.state_id)
    ancestry = ancestry or RecognitionAncestry(route)
    if ancestry.route is not route:
        raise ValueError("Recognition ancestry belongs to another route invocation.")
    ancestor, positions = ancestry.resolve, ancestry.positions
    programs = {p.program_id: p for p in route.construction_program.reaction_programs}
    result = []
    for transition in route.construction_program.transitions:
        mapping = transition.reaction_boundary_mapping
        if mapping is None:
            continue
        if len(mapping.pre_strands) != 2:
            raise ValueError("Recognition footprint requires a recorded duplex boundary mapping.")
        top, bottom = mapping.pre_strands
        if len(top.sequence) != len(bottom.sequence):
            raise ValueError("Recognition footprint requires the declared precursor duplex.")
        program = programs[mapping.reaction_program_id]
        for stage in program.stages:
            require_precursor_frame(program, stage)
            for operation in stage.operations:
                binding = operation.intended_binding
                a, z = binding.recognition_span.start.offset, binding.recognition_span.end.offset
                origins = tuple(ancestor(top.lineage[i]) for i in range(a, z)) + tuple(
                    ancestor(bottom.lineage[len(top.sequence) - 1 - i]) for i in range(a, z)
                )
                current = positions[state_index]
                recognition = tuple(
                    sorted(
                        {address for origin in origins for address in current.get(origin, ())},
                        key=lambda address: (address.strand_id, address.index),
                    )
                )
                matched = sum(bool(current.get(origin)) for origin in origins)
                presence: Literal["present", "partial", "not_yet_present", "removed", "unresolved"]
                if any(len(current.get(origin, ())) > 1 for origin in origins):
                    presence = "unresolved"
                elif matched == len(origins):
                    presence = "present"
                elif matched:
                    presence = "partial"
                elif any(any(p.get(o) for o in origins) for p in positions[:state_index]):
                    presence = "removed"
                elif any(any(p.get(o) for o in origins) for p in positions[state_index + 1 :]):
                    presence = "not_yet_present"
                else:
                    presence = "unresolved"
                # Keep precursor reference-coordinate order, including when the
                # represented strand runs backwards in a folded drawing. A repeat
                # has no unique orientation anchor and must not receive a guessed arrow.
                orientation_path: tuple[MolecularAddress, ...] = ()
                for half in (origins[: len(origins) // 2], origins[len(origins) // 2 :]):
                    anchors = tuple(current[o][0] for o in half if len(current.get(o, ())) == 1)
                    if len(anchors) >= 2:
                        orientation_path = anchors
                        break
                result.append(
                    InspectionRecognitionSite(
                        site_id=operation.operation_id,
                        enzyme_id=operation.enzyme_id,
                        enzyme_name=names.get(operation.enzyme_id, operation.enzyme_id),
                        role=inspection_operation_role(route, operation, mapping.pre_state_id),
                        orientation=binding.orientation.value,
                        precursor_state_id=mapping.pre_state_id,
                        presence=presence,
                        reference_base_count=len(origins),
                        mapped_reference_bases=matched,
                        recognition=recognition,
                        orientation_path=orientation_path,
                    )
                )
    return tuple(result)
