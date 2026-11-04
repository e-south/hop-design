"""Project anatomy and address relationships only from verified state and material lineage."""

from collections import defaultdict
from typing import Literal

from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.projections.inspection import (
    InspectionBase,
    InspectionStateChoice,
    MolecularStateInspection,
)
from hop_design.models.construction.projections.neighborhoods import molecular_neighborhood
from hop_design.models.construction.projections.route_view import MolecularRouteView
from hop_design.models.construction.variants.inspection import MolecularAddress
from hop_design.models.molecular_state import MaterialBaseLineage, StrandEnd

from ..comparison_regions import region_spans
from .inspection_annotations import inspection_interfaces, inspection_operations
from .inspection_bonds import inspection_bonds
from .inspection_layout import inspection_layout_frame
from .inspection_sites import RecognitionAncestry, inspection_recognition_sites


def inspection_states(route: MolecularRouteView) -> tuple[ConstructionState, ...]:
    return (route.source_preparation.input_state, *route.construction_program.states)


def resolve_inspection_states(
    route: MolecularRouteView, selector: str
) -> tuple[ConstructionState, ...]:
    """Roles, exact state ids and semantic phases are distinct supported selectors."""
    states = inspection_states(route)
    roles = {
        "hairpin": describe_hairpin(route).state.state_id,
        "endpoint": states[-1].state_id,
        "source_material": states[0].state_id,
    }
    selected = roles.get(selector, selector)
    exact = tuple(s for s in states if s.state_id == selected)
    return exact or tuple(s for s in states if s.phase.value == selected)


def _address(state: ConstructionState, strand: str, index: int) -> MolecularAddress:
    return MolecularAddress(state_id=state.state_id, strand_id=strand, index=index)


def _lineage_at(
    states: tuple[ConstructionState, ...], address: MolecularAddress
) -> MaterialBaseLineage:
    for state in states:
        if state.state_id == address.state_id:
            for strand in state.molecules:
                if strand.strand_id == address.strand_id and address.index < len(strand.lineage):
                    return strand.lineage[address.index]
    raise ValueError("Unknown molecular address in this preparation's recorded states.")


def project_molecular_inspection(
    route: MolecularRouteView,
    selector: str,
    focus: MolecularAddress | None = None,
    *,
    enzyme_names: dict[str, str] | None = None,
    recognition_ancestry: RecognitionAncestry | None = None,
) -> MolecularStateInspection:
    states = inspection_states(route)
    anatomy = describe_hairpin(route)
    state_matches = resolve_inspection_states(route, selector)
    if not state_matches:
        raise ValueError("Unknown or unavailable inspection state for this preparation.")
    if len(state_matches) > 1:
        raise ValueError("Ambiguous inspection phase; name an exact recorded state id.")
    state = state_matches[0]
    state_id = state.state_id
    prep = route.source_preparation
    upstream = {b.material_use.use_id: b.upstream_lineage for b in prep.produced_material_bindings}

    def ancestor(base: MaterialBaseLineage) -> tuple[str, int]:
        # Prepared duplex bases carry explicit upstream lineage. Do not align sequences.
        if base.origin_id in upstream:
            base = upstream[base.origin_id][base.origin_index]
        return base.origin_id, base.origin_index

    regions: dict[tuple[str, int], set[str]] = defaultdict(set)
    direct_regions: dict[tuple[str, int], set[str]] = defaultdict(set)
    for base in anatomy.state.molecules[0].lineage:
        for name, (start, end) in region_spans(anatomy).items():
            if start <= base.product_index < end:
                regions[ancestor(base)].add(name)
                direct_regions[base.origin_id, base.origin_index].add(name)
    roles = {
        use.use_id: use.role.value
        for use in (
            *route.material_uses,
            prep.source_ssdna_use,
            prep.forward_primer_use,
            prep.reverse_primer_use,
        )
    }
    paired: dict[tuple[str, int], list[MolecularAddress]] = defaultdict(list)
    for pair in state.pairings:
        left, right = (
            (pair.left_strand_id, pair.left_index),
            (pair.right_strand_id, pair.right_index),
        )
        paired[left].append(_address(state, *right))
        paired[right].append(_address(state, *left))
    origin = _lineage_at(states, focus) if focus is not None else None
    matches = {
        (strand.strand_id, base.product_index)
        for strand in state.molecules
        for base in strand.lineage
        if origin is not None and ancestor(base) == ancestor(origin)
    }
    partner_matches = {(a.strand_id, a.index) for position in matches for a in paired[position]}
    interfaces: set[tuple[str, int]] = set()
    if state.state_id == states[-1].state_id:
        lengths = {s.strand_id: len(s.sequence) for s in state.molecules}
        for interface in route.final_product.cohesive_ends:
            start = (
                0
                if interface.overhang_end is StrandEnd.FIVE_PRIME
                else lengths[interface.protruding_strand_id] - len(interface.sequence)
            )
            interfaces.update(
                (interface.protruding_strand_id, i)
                for i in range(start, start + len(interface.sequence))
            )
    bases = []
    for strand_index, strand in enumerate(state.molecules):
        for base in strand.lineage:
            address = _address(state, strand.strand_id, base.product_index)
            position = (strand.strand_id, base.product_index)
            names = direct_regions.get(
                (base.origin_id, base.origin_index), regions.get(ancestor(base), set())
            )
            region = next(iter(names)) if len(names) == 1 else None
            categories = {molecular_neighborhood(name) for name in names}
            if region is None and len(categories) == 1:
                region = next(iter(categories))
            relation: Literal["same_address", "retained", "copied", "paired"] | None = None
            if address == focus:
                relation = "same_address"
            elif position in matches:
                relation = (
                    "retained"
                    if origin is not None
                    and (base.origin_id, base.origin_index, base.origin_strand)
                    == (origin.origin_id, origin.origin_index, origin.origin_strand)
                    else "copied"
                )
            elif position in partner_matches:
                relation = "paired"
            bases.append(
                InspectionBase(
                    address=address,
                    strand_index=strand_index,
                    base=strand.sequence[base.product_index],
                    region=region,
                    neighborhood="interfaces"
                    if position in interfaces
                    else molecular_neighborhood(region),
                    origin=base,
                    material_role=roles.get(base.origin_id),
                    paired_addresses=tuple(paired[position]),
                    focus_relation=relation,
                )
            )
    choices = []
    for item in states:
        roles_for_state: list[Literal["source", "hairpin", "endpoint"]] = []
        if item.state_id == states[0].state_id:
            roles_for_state.append("source")
        if item.state_id == anatomy.state.state_id:
            roles_for_state.append("hairpin")
        if item.state_id == states[-1].state_id:
            roles_for_state.append("endpoint")
        choices.append(
            InspectionStateChoice(
                state_id=item.state_id, phase=item.phase.value, roles=tuple(roles_for_state)
            )
        )
    focus_status: Literal["not_requested", "mapped", "removed", "not_yet_present", "not_present"]
    focus_status = "not_requested" if focus is None else "mapped" if matches else "not_present"
    if focus_status == "not_present" and origin is not None:
        # The verified trajectory is ordered. Distinguish loss from a material that
        # enters later, using ancestry in recorded states rather than equal bases.
        current_index = next(i for i, item in enumerate(states) if item.state_id == state_id)
        occurrences = [
            i
            for i, item in enumerate(states)
            if any(
                ancestor(base) == ancestor(origin)
                for strand in item.molecules
                for base in strand.lineage
            )
        ]
        if any(i < current_index for i in occurrences):
            focus_status = "removed"
        elif any(i > current_index for i in occurrences):
            focus_status = "not_yet_present"
    return MolecularStateInspection(
        state=state,
        materialized_realization_id=route.materialized_realization_id,
        available_states=tuple(choices),
        bases=tuple(bases),
        focus=focus,
        focus_status=focus_status,
        layout_frame=inspection_layout_frame(state, states),
        operations=inspection_operations(route, state, enzyme_names or {}),
        recognition_sites=inspection_recognition_sites(
            route, state, enzyme_names or {}, ancestry=recognition_ancestry
        ),
        interfaces=inspection_interfaces(route, state),
        formed_bond_boundaries=inspection_bonds(state, states),
    )
