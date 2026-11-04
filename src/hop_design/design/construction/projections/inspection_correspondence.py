"""Map retained/copied parts and declared regional comparisons; never align whole sequences."""

from collections import defaultdict
from typing import Literal

from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.projections.inspection_transition import (
    InspectionCorrespondence,
    InspectionTransition,
)
from hop_design.models.construction.projections.route_view import MolecularRouteView
from hop_design.models.construction.variants.inspection import MolecularAddress

from ..comparison_regions import region_spans
from .inspection_layout import Origin, lineage_key
from .inspection_lineage import ancestry_resolver
from .sequence_difference import compare_sequence_region


def _positions(
    route: MolecularRouteView, state: ConstructionState, *, upstream: bool = False
) -> dict[Origin, list[MolecularAddress]]:
    resolve = ancestry_resolver(route) if upstream else lineage_key
    result = defaultdict(list)
    for molecule in state.molecules:
        for base in molecule.lineage:
            result[resolve(base)].append(
                MolecularAddress(
                    state_id=state.state_id, strand_id=molecule.strand_id, index=base.product_index
                )
            )
    return result


def _oriented(key: Origin, complement: bool) -> Origin:
    if not complement:
        return key
    return key[0], "complementary" if key[1] == "primary" else "primary", key[2]


def inspection_correspondence(
    reference_route: MolecularRouteView,
    reference: ConstructionState,
    target_route: MolecularRouteView,
    target: ConstructionState,
) -> InspectionTransition:
    same_route = (
        reference_route.materialized_realization_id == target_route.materialized_realization_id
    )
    before, after = _positions(reference_route, reference), _positions(target_route, target)
    links: dict[tuple[MolecularAddress, MolecularAddress], InspectionCorrespondence] = {}
    notices = []

    def link(
        a: MolecularAddress,
        b: MolecularAddress,
        relation: Literal["retained", "copied", "comparison"],
    ) -> None:
        links.setdefault((a, b), InspectionCorrespondence(reference=a, target=b, relation=relation))

    for origin in before.keys() & after.keys():
        if len(before[origin]) == len(after[origin]) == 1:
            link(before[origin][0], after[origin][0], "retained")
        else:
            notices.append("Repeated material ancestry has no unique retained-position mapping.")
    old = _positions(reference_route, reference, upstream=True)
    new = _positions(target_route, target, upstream=True)
    if same_route:
        # A retained base stays its own anchor. Only a newly represented base
        # needs a copying source; a paired partner is not another retained identity.
        retained = {b for _, b in links}
        target_origins = {address: key for key, values in new.items() for address in values}
        for origin, targets in after.items():
            direct_sources = {
                a
                for key, values in before.items()
                if (key[0], key[2]) == (origin[0], origin[2])
                for a in values
            }
            for b in targets:
                if b in retained:
                    continue
                key = target_origins[b]
                sources = direct_sources or {
                    a
                    for candidate, values in old.items()
                    if (candidate[0], candidate[2]) == (key[0], key[2])
                    for a in values
                }
                if len(sources) == 1:
                    link(next(iter(sources)), b, "copied")
                elif sources:
                    notices.append("Copy ancestry has multiple possible source positions.")
    else:
        left, right = describe_hairpin(reference_route), describe_hairpin(target_route)
        a_strand, b_strand = left.state.molecules[0], right.state.molecules[0]
        a_regions, b_regions = region_spans(left), region_spans(right)
        a_origin, b_origin = ancestry_resolver(reference_route), ancestry_resolver(target_route)
        for region, a_span in a_regions.items():
            b_span = b_regions[region]
            comparison = compare_sequence_region(
                region,
                a_strand.sequence[slice(*a_span)],
                b_strand.sequence[slice(*b_span)],
                a_span,
                b_span,
            )
            if comparison.correspondence in ("ambiguous_minimum_edit", "unresolved_budget"):
                notices.append(
                    f"Position correspondence unresolved: {region} "
                    f"({comparison.reference_sequence} → {comparison.observed_sequence})."
                )
            for column in comparison.columns:
                if column.reference_offset is None or column.observed_offset is None:
                    continue
                a_key = a_origin(a_strand.lineage[a_span[0] + column.reference_offset])
                b_key = b_origin(b_strand.lineage[b_span[0] + column.observed_offset])
                for complement in (False, True):
                    aa, bb = old[_oriented(a_key, complement)], new[_oriented(b_key, complement)]
                    if len(aa) == len(bb) == 1:
                        link(aa[0], bb[0], "comparison")
                    elif aa and bb:
                        notices.append(
                            f"Position correspondence unresolved: repeated {region} ancestry."
                        )
    addresses_before = {a for values in before.values() for a in values}
    addresses_after = {a for values in after.values() for a in values}
    mapped_before = {a for a, _ in links}
    mapped_after = {b for _, b in links}

    def order(a: MolecularAddress) -> tuple[str, str, int]:
        return a.state_id, a.strand_id, a.index

    return InspectionTransition(
        reference_state_id=reference.state_id,
        target_state_id=target.state_id,
        mode="processing" if same_route else "variant",
        links=tuple(
            links[key] for key in sorted(links, key=lambda pair: (order(pair[0]), order(pair[1])))
        ),
        unmapped_reference=tuple(sorted(addresses_before - mapped_before, key=order)),
        unmapped_target=tuple(sorted(addresses_after - mapped_after, key=order)),
        notices=tuple(sorted(set(notices))),
    )
