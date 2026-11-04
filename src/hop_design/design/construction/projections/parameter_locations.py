"""Locate parameter measurements on admitted states and follow their material ancestry."""

from collections.abc import Iterable
from typing import Any, cast

from hop_design.models.construction.complete.pcr.authority import AdapterAnnealingAuthority
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.projections.atlas import MolecularScenes
from hop_design.models.construction.projections.route_view import MolecularRouteView
from hop_design.models.construction.targets import BasalTarget, FoldbackTarget
from hop_design.models.construction.variants.inspection import MolecularAddress
from hop_design.models.construction.variants.parameters import parameter_definition

from .inspection_annotations import address, boundary
from .inspection_lineage import ancestry_resolver, boundary_occurrences, span_occurrences


def parameter_locations(
    route: MolecularRouteView,
    atlas: MolecularScenes,
    parameter_values: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    anatomy = describe_hairpin(route)
    state = anatomy.state
    strand = state.molecules[0]
    f = cast(FoldbackTarget, route.foldback_authority.local_realization.achieved_geometry)
    ancestor = ancestry_resolver(route)
    bases = {base.address: base for s in atlas.states for base in s.bases}
    base_origins = {
        a: (resolved[0], resolved[2])
        for a, base in bases.items()
        for resolved in (ancestor(base.origin),)
    }
    locations: dict[str, set[MolecularAddress]] = {}
    anchors: dict[str, list[dict[str, Any]]] = {}
    parameter_values = parameter_values or {}

    def located_span(key: str, molecule_state: Any, strand_id: str, start: int, end: int) -> None:
        locations.setdefault(key, set()).update(
            address(molecule_state, strand_id, i) for i in range(start, end)
        )
        anchors.setdefault(key, []).append(
            {
                "start": boundary(molecule_state, strand_id, start).model_dump(mode="json"),
                "end": boundary(molecule_state, strand_id, end).model_dump(mode="json"),
            }
        )

    def span(key: str, start: int, end: int) -> None:
        located_span(key, state, strand.strand_id, start, end)

    source_preparation = route.source_preparation
    prepared = source_preparation.product_state
    source_strand = prepared.molecules[0]
    source_end = len(source_strand.sequence)
    for direction, flank_start, flank_end in (
        ("forward", 0, source_preparation.payload_source_span.start.offset),
        ("reverse", source_preparation.payload_source_span.end.offset, source_end),
    ):
        required = parameter_values.get(
            f"source_{direction}_primer_required_nt",
            getattr(source_preparation, f"{direction}_primer").annealing_length_nt,
        )
        located_span(
            f"source_{direction}_primer_available_nt",
            prepared,
            source_strand.strand_id,
            flank_start,
            flank_end,
        )
        located_span(
            f"source_{direction}_primer_required_nt",
            prepared,
            source_strand.strand_id,
            0 if direction == "forward" else source_end - required,
            required if direction == "forward" else source_end,
        )

    a, z = anatomy.stem_primary_span.end.offset, anatomy.loop_span.start.offset
    b, y = anatomy.loop_span.end.offset, anatomy.stem_return_span.start.offset
    d = f.junction_offset_nt
    # These two spans are the opposing positions of the same paired coordinate.
    for key, left, right in (
        ("foldback_arm_bp", (a, z), (b, y)),
        ("loop_side_paired_bp", (a, z), (b, y)),
        ("join_offset_nt", (a, a + d), (y - d, y)),
        ("self_paired_arm_bp", (a + d, z), (b, y - d)),
    ):
        span(key, *left)
        span(key, *right)
    if a + d not in anatomy.join_boundaries and y - d not in anatomy.join_boundaries:
        raise ValueError("Foldback parameter projection requires its recorded ligation boundary.")
    for key in ("loop_nt", "loop_word"):
        span(key, z, b)
    span(
        "open_side_paired_positions",
        anatomy.paired_primary_span.start.offset,
        anatomy.stem_primary_span.start.offset,
    )
    span(
        "open_side_paired_positions",
        anatomy.stem_return_span.end.offset,
        anatomy.paired_return_span.end.offset,
    )
    span("five_prime_unpaired_nt", 0, anatomy.paired_primary_span.start.offset)
    span("three_prime_unpaired_nt", anatomy.paired_return_span.end.offset, len(strand.sequence))
    for pair in anatomy.ordered_contacts:
        if (
            pair.kind.value != "watson_crick"
            and pair.left_index < anatomy.stem_primary_span.start.offset
        ):
            locations.setdefault("noncanonical_pairs", set()).update(
                (
                    address(state, pair.left_strand_id, pair.left_index),
                    address(state, pair.right_strand_id, pair.right_index),
                )
            )
    locations.setdefault("noncanonical_pairs", set())
    if route.basal_authority:
        target = cast(BasalTarget, route.basal_authority.local_realization.achieved_geometry)
        prepared = route.source_preparation.product_state
        start = route.payload_source_map.segments[0].source_span.start.offset
        located_span(
            "basal_nick_offset_nt",
            prepared,
            prepared.molecules[0].strand_id,
            start - target.nick_offset_nt,
            start,
        )
    for transition in route.construction_program.transitions:
        authority = transition.pcr_authority
        if not isinstance(authority, AdapterAnnealingAuthority):
            continue
        associated = next(
            s.state for s in atlas.states if s.state.state_id == authority.post_state_id
        )
        local_count = (
            len(route.basal_authority.projection.pairing_state.pairs)
            if route.basal_authority
            else 0
        )
        minimum = parameter_values.get("adapter_annealing_min_nt")
        pairs = sorted(authority.pairings, key=lambda p: p.right_index)
        for rank, pair in enumerate(pairs):
            i = pair.right_index - authority.adapter_span.start.offset
            source = address(associated, pair.left_strand_id, pair.left_index)
            adapter = address(associated, pair.right_strand_id, pair.right_index)
            locations.setdefault("adapter_annealing_achieved_nt", set()).update((source, adapter))
            if minimum is not None and rank < minimum:
                locations.setdefault("adapter_annealing_min_nt", set()).update((source, adapter))
            if i < local_count:
                locations[f"basal_source_base_{i}"] = {source}
                locations[f"basal_adapter_base_{i}"] = {adapter}
                locations[f"basal_pair_class_{i}"] = {source, adapter}
        if minimum is not None:
            # The minimum is a threshold from the ligation side, not all achieved contacts.
            first = authority.adapter_span.start.offset
            anchors["adapter_annealing_min_nt"] = [
                {
                    "start": boundary(associated, pairs[0].right_strand_id, first).model_dump(
                        mode="json"
                    ),
                    "end": boundary(
                        associated, pairs[0].right_strand_id, first + minimum
                    ).model_dump(mode="json"),
                }
            ]
    for inspection in atlas.states:
        for operation in inspection.operations:
            if operation.timing != "planned":
                continue
            method_key = {
                "foldback_nick": "foldback_method",
                "basal_nick": "basal_method",
                "end_generation": "release_method",
            }.get(operation.role)
            for cut in operation.cuts:
                adjacent = {a for a in (cut.boundary.before, cut.boundary.after) if a}
                keys = [method_key] if method_key else []
                if operation.role in ("foldback_nick", "basal_nick"):
                    keys.append(operation.role.removesuffix("_nick") + "_strand")
                for key in keys:
                    locations.setdefault(key, set()).update(adjacent)
                    cut_anchor = cut.boundary.model_dump(mode="json")
                    anchors.setdefault(key, []).append({"start": cut_anchor, "end": cut_anchor})
        for interface in inspection.interfaces:
            prefix = interface.side
            for key in (f"{prefix}_end_word", f"{prefix}_end_polarity"):
                locations[key] = set(interface.overhang)
            start_boundary, end_boundary = interface.paired_start, interface.paired_end
            anchor = start_boundary.after or start_boundary.before
            assert anchor is not None
            lo = (
                start_boundary.after.index
                if start_boundary.after
                else cast(MolecularAddress, start_boundary.before).index + 1
            )
            hi = (
                end_boundary.after.index
                if end_boundary.after
                else cast(MolecularAddress, end_boundary.before).index + 1
            )
            locations[f"{prefix}_gap"] = {
                MolecularAddress(state_id=anchor.state_id, strand_id=anchor.strand_id, index=i)
                for i in range(lo, hi)
            }
            anchors[f"{prefix}_gap"] = [
                {
                    "start": start_boundary.model_dump(mode="json"),
                    "end": end_boundary.model_dump(mode="json"),
                }
            ]
        for site in inspection.recognition_sites:
            method_key = {
                "foldback_nick": "foldback_method",
                "basal_nick": "basal_method",
                "end_generation": "release_method",
            }.get(site.role)
            if method_key:
                locations.setdefault(method_key, set()).update(site.recognition)
    result = []
    release_cuts = [
        cut.boundary.model_dump(mode="json")
        for inspection in atlas.states
        for operation in inspection.operations
        if operation.role == "end_generation"
        for cut in operation.cuts
    ]
    for key, references in sorted(locations.items()):
        origins = {base_origins[a] for a in references}
        occurrences = [a for a, base in bases.items() if base_origins[a] in origins]

        def ordered(addresses: Iterable[MolecularAddress]) -> list[dict[str, Any]]:
            return [
                a.model_dump(mode="json")
                for a in sorted(addresses, key=lambda a: (a.state_id, a.strand_id, a.index))
            ]

        result.append(
            {
                "key": key,
                "definition": parameter_definition(key).model_dump(mode="json"),
                "reference_addresses": ordered(references),
                "boundary_anchors": anchors.get(key, []),
                "boundary_occurrences": boundary_occurrences(
                    anchors.get(key, []), base_origins, cuts=release_cuts
                )
                if not references
                else span_occurrences(anchors.get(key, []), base_origins)
                if key
                in {"basal_nick_offset_nt", "adapter_annealing_min_nt", "left_gap", "right_gap"}
                else anchors.get(key, []),
                "occurrences": ordered(occurrences),
                "correspondence": "recorded_material_ancestry_including_copies",
                "zero_extent": not references,
            }
        )
    return result
