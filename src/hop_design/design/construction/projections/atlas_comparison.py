"""Compare verified routes through region-local sequence and recorded occurrence identity."""

from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.projections.atlas import (
    AtlasBaseSubstitution,
    AtlasComparison,
    AtlasMaterialDifference,
)
from hop_design.models.construction.projections.inspection_transition import InspectionTransition
from hop_design.models.construction.projections.materials import external_material_uses
from hop_design.models.construction.projections.sequence_difference import SequenceRegionDifference
from hop_design.models.construction.variants.inspection import MolecularAddress

from ..comparison_regions import region_spans
from .inspection import inspection_states, resolve_inspection_states
from .inspection_correspondence import inspection_correspondence
from .inspection_lineage import ancestry_resolver
from .sequence_difference import compare_sequence_region


def view_states(
    route: MaterializedConstructionRealization, selector: str
) -> tuple[ConstructionState, ...]:
    return (
        inspection_states(route)
        if selector == "all"
        else resolve_inspection_states(route, selector)
    )


def atlas_correspondence(
    old: MaterializedConstructionRealization,
    before: str,
    new: MaterializedConstructionRealization,
    after: str,
) -> tuple[InspectionTransition, ...]:
    left, right = view_states(old, before), view_states(new, after)
    if before != "all" and len(left) != 1:
        raise ValueError("Preceding molecular view must name one recorded state or all.")
    if after != "all" and len(right) != 1:
        raise ValueError("Target molecular view must name one recorded state or all.")
    if before != "all" and after != "all":
        return (inspection_correspondence(old, left[0], new, right[0]),)
    # Shared phase is a semantic match only when unique on both routes.
    return tuple(
        inspection_correspondence(old, a, new, b)
        for a in left
        for b in right
        if a.phase == b.phase
        and sum(s.phase == a.phase for s in left) == 1
        and sum(s.phase == b.phase for s in right) == 1
    )


def compare_route_atlases(
    old: MaterializedConstructionRealization,
    new: MaterializedConstructionRealization,
    *,
    reference: str,
    option: str,
) -> AtlasComparison:
    """Exact sequences always remain visible; only supported correspondence marks bases."""
    if old.final_product.reference.endpoint != new.final_product.reference.endpoint:
        raise ValueError("Compared molecular preparations must request the same endpoint.")
    transitions = atlas_correspondence(old, "all", new, "all")
    before = {
        (s.state_id, m.strand_id, i): base
        for s in inspection_states(old)
        for m in s.molecules
        for i, base in enumerate(m.sequence)
    }
    after = {
        (s.state_id, m.strand_id, i): base
        for s in inspection_states(new)
        for m in s.molecules
        for i, base in enumerate(m.sequence)
    }
    substitutions = []
    for transition in transitions:
        for link in transition.links:
            a, b = link.reference, link.target
            reference_base, observed_base = (
                before[a.state_id, a.strand_id, a.index],
                after[b.state_id, b.strand_id, b.index],
            )
            if reference_base != observed_base and link.relation == "comparison":
                substitutions.append(
                    AtlasBaseSubstitution(
                        address=b, reference_base=reference_base, observed_base=observed_base
                    )
                )
    left, right = describe_hairpin(old), describe_hairpin(new)
    a_spans, b_spans = region_spans(left), region_spans(right)
    regions = tuple(
        compare_sequence_region(
            region,
            left.state.molecules[0].sequence[slice(*a_span)],
            right.state.molecules[0].sequence[slice(*b_spans[region])],
            a_span,
            b_spans[region],
        )
        for region, a_span in a_spans.items()
    )
    materials = [{u.role.value: m for m, u in external_material_uses(r)} for r in (old, new)]
    changed = tuple(
        AtlasMaterialDifference(
            role=role, reference=materials[0].get(role), observed=materials[1].get(role)
        )
        for role in sorted(set(materials[0]) | set(materials[1]))
        if materials[0].get(role) != materials[1].get(role)
    )
    loop = next(r for r in regions if r.region == "loop")
    endpoint_regions = tuple(
        compare_sequence_region(
            f"strand_{i + 1}",
            a.sequence,
            b.sequence,
            (0, len(a.sequence)),
            (0, len(b.sequence)),
        )
        for i, (a, b) in enumerate(
            zip(old.final_product.strands, new.final_product.strands, strict=True)
        )
    )
    additions, unresolved = _regional_occurrences(new, regions)
    endpoint_changes, endpoint_added, endpoint_unknown = _endpoint_marks(
        new,
        endpoint_regions,
        transitions,
        set(additions) | set(unresolved) | {s.address for s in substitutions},
    )
    return AtlasComparison(
        reference=reference,
        option_label=option,
        transitions=transitions,
        substitutions=(*substitutions, *endpoint_changes),
        notices=tuple(sorted({n for t in transitions for n in t.notices})),
        material_roles=tuple(m.role for m in changed),
        reference_loop=loop.reference_sequence,
        observed_loop=loop.observed_sequence,
        regions=regions,
        endpoint_regions=endpoint_regions,
        materials=changed,
        additions=(*additions, *endpoint_added),
        unresolved_positions=(*unresolved, *endpoint_unknown),
    )


def _endpoint_marks(
    route: MaterializedConstructionRealization,
    regions: tuple[SequenceRegionDifference, ...],
    transitions: tuple[InspectionTransition, ...],
    already_marked: set[MolecularAddress],
) -> tuple[
    tuple[AtlasBaseSubstitution, ...], tuple[MolecularAddress, ...], tuple[MolecularAddress, ...]
]:
    """Endpoint display edits cannot imply additions to an earlier hairpin.

    Prefer recorded ancestry and regional correspondence. Compare remaining
    endpoint positions literally, without propagating these edits upstream.
    """
    endpoint = inspection_states(route)[-1]
    eligible = {
        a for t in transitions if t.target_state_id == endpoint.state_id for a in t.unmapped_target
    } - already_marked
    changes, added, unknown = [], [], []
    for strand, region in zip(route.final_product.strands, regions, strict=True):
        uncertain = region.correspondence in ("ambiguous_minimum_edit", "unresolved_budget")
        for i in range(len(strand.sequence)):
            address = MolecularAddress(
                state_id=endpoint.state_id, strand_id=strand.strand_id, index=i
            )
            if uncertain and address in eligible:
                unknown.append(address)
        for column in region.columns:
            if column.observed_offset is None:
                continue
            address = MolecularAddress(
                state_id=endpoint.state_id,
                strand_id=strand.strand_id,
                index=column.observed_offset,
            )
            if address not in eligible:
                continue
            if column.kind == "added":
                added.append(address)
            elif column.kind == "substitution":
                assert column.reference_base is not None and column.observed_base is not None
                changes.append(
                    AtlasBaseSubstitution(
                        address=address,
                        reference_base=column.reference_base,
                        observed_base=column.observed_base,
                    )
                )
    return tuple(changes), tuple(added), tuple(unknown)


def _regional_occurrences(
    route: MaterializedConstructionRealization,
    regions: tuple[SequenceRegionDifference, ...],
) -> tuple[tuple[MolecularAddress, ...], tuple[MolecularAddress, ...]]:
    """Follow declared regional additions/uncertainty through recorded copy ancestry."""
    strand = describe_hairpin(route).state.molecules[0]
    resolve = ancestry_resolver(route)
    added: set[tuple[str, int]] = set()
    unresolved: set[tuple[str, int]] = set()
    for region in regions:
        uncertain = region.correspondence in ("ambiguous_minimum_edit", "unresolved_budget")
        offsets = (
            range(len(region.observed_sequence))
            if uncertain
            else (c.observed_offset for c in region.columns if c.kind == "added")
        )
        for offset in offsets:
            assert offset is not None
            origin = resolve(strand.lineage[region.observed_span[0] + offset])
            (unresolved if uncertain else added).add((origin[0], origin[2]))
    additions, unknown = [], []
    for state in inspection_states(route):
        for molecule in state.molecules:
            for base in molecule.lineage:
                origin = resolve(base)
                key = (origin[0], origin[2])
                address = MolecularAddress(
                    state_id=state.state_id, strand_id=molecule.strand_id, index=base.product_index
                )
                if key in added:
                    additions.append(address)
                if key in unresolved:
                    unknown.append(address)
    return tuple(additions), tuple(unknown)
