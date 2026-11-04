"""Resolve recorded produced-material ancestry without aligning sequence letters."""

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from hop_design.models.construction.projections.route_view import MolecularRouteView
from hop_design.models.construction.variants.inspection import MolecularAddress
from hop_design.models.molecular_state import LineageStrand, MaterialBaseLineage
from hop_design.serialization import canonical_json_bytes

from .inspection_layout import Origin, lineage_key


def ancestry_resolver(
    route: MolecularRouteView,
) -> Callable[[MaterialBaseLineage], Origin]:
    prep = route.source_preparation
    upstream = {b.material_use.use_id: b.upstream_lineage for b in prep.produced_material_bindings}
    native = {
        b.origin_id: b.origin_strand
        for strand in prep.product_state.molecules
        for b in strand.lineage
    }

    def resolve(base: MaterialBaseLineage) -> Origin:
        if base.origin_id not in upstream:
            return lineage_key(base)
        source = upstream[base.origin_id][base.origin_index]
        strand = source.origin_strand
        if base.origin_strand != native[base.origin_id]:
            strand = (
                LineageStrand.COMPLEMENTARY
                if strand is LineageStrand.PRIMARY
                else LineageStrand.PRIMARY
            )
        return source.origin_id, strand.value, source.origin_index

    return resolve


def boundary_occurrences(
    anchors: list[dict[str, Any]],
    origins: dict[MolecularAddress, tuple[str, int]],
    *,
    cuts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    found = {canonical_json_bytes(a): a for a in anchors}
    complete = list(anchors)
    for anchor in anchors:
        if anchor["start"] != anchor["end"]:
            continue
        edge = anchor["start"]
        if (edge["before"] is None) == (edge["after"] is None):
            continue
        side = "before" if edge["before"] else "after"
        surviving = origins.get(MolecularAddress.model_validate(edge[side]))
        candidates = {}
        for cut in cuts or []:
            if cut["before"] is None or cut["after"] is None:
                continue
            pair = tuple(
                origins.get(MolecularAddress.model_validate(cut[k])) for k in ("before", "after")
            )
            if None not in pair and surviving == pair[0 if side == "before" else 1]:
                candidates[pair] = cut
        if len(candidates) == 1:
            cut = next(iter(candidates.values()))
            complete.append({"start": cut, "end": cut})
    for anchor in complete:
        if anchor["start"] != anchor["end"]:
            continue
        edge = anchor["start"]
        if edge["before"] is None or edge["after"] is None:
            # Without one recorded cut context, a terminus cannot establish adjacency.
            continue
        pair = tuple(
            origins.get(MolecularAddress.model_validate(a)) for a in (edge["before"], edge["after"])
        )
        if None in pair:
            continue
        for left, origin in origins.items():
            right = MolecularAddress(
                state_id=left.state_id, strand_id=left.strand_id, index=left.index + 1
            )
            candidate = (origin, origins.get(right))
            if candidate != pair and candidate != tuple(reversed(pair)):
                continue
            boundary = {
                "before": left.model_dump(mode="json"),
                "after": right.model_dump(mode="json"),
            }
            item = {"start": boundary, "end": boundary}
            found[canonical_json_bytes(item)] = item
    return [found[key] for key in sorted(found)]


def span_occurrences(
    anchors: list[dict[str, Any]], origins: dict[MolecularAddress, tuple[str, int]]
) -> list[dict[str, Any]]:
    """Locate a complete ordered span, including reverse copies, without alignment.

    These are measurement boundaries, not inferred cuts. An absent or interrupted
    ancestral run cannot establish a span on the inspected molecule.
    """
    found = {canonical_json_bytes(a): a for a in anchors}
    by_origin: dict[tuple[str, int], list[MolecularAddress]] = defaultdict(list)
    for address, origin in origins.items():
        by_origin[origin].append(address)
    for anchor in anchors:
        start = anchor["start"]["after"]
        end = anchor["end"]["before"]
        if (
            not start
            or not end
            or (start["state_id"], start["strand_id"]) != (end["state_id"], end["strand_id"])
        ):
            continue
        n = end["index"] - start["index"] + 1
        if n <= 0:
            continue
        first = MolecularAddress.model_validate(start)
        sequence = tuple(
            origins.get(first.model_copy(update={"index": i}))
            for i in range(start["index"], end["index"] + 1)
        )
        if None in sequence:
            continue
        for ordered in (sequence, tuple(reversed(sequence))):
            first_origin = ordered[0]
            assert first_origin is not None
            for a in by_origin[first_origin]:
                addresses = tuple(a.model_copy(update={"index": a.index + i}) for i in range(n))
                if tuple(origins.get(b) for b in addresses) != ordered:
                    continue
                before = a.model_copy(update={"index": a.index - 1}) if a.index else None
                after = a.model_copy(update={"index": a.index + n})
                item = {
                    "start": {
                        "before": before.model_dump(mode="json") if before in origins else None,
                        "after": a.model_dump(mode="json"),
                    },
                    "end": {
                        "before": addresses[-1].model_dump(mode="json"),
                        "after": after.model_dump(mode="json") if after in origins else None,
                    },
                }
                found[canonical_json_bytes(item)] = item
    return [found[key] for key in sorted(found)]
