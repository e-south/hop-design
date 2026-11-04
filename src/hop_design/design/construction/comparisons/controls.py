"""Compare regional products through exact ancestry, separately from preparation history."""

from collections import Counter, defaultdict
from typing import Any

from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.stage_controls import ResolvedStageControl
from hop_design.models.molecular_state import MolecularStrand, StrandPairObservation

from ..comparison_regions import region_spans

type StageContext = tuple[
    tuple[MolecularStrand, ...], tuple[StrandPairObservation, ...], list[list[str | None]]
]


def stage_facts(route: MaterializedConstructionRealization) -> dict[str, Any]:
    return {stage: _facts(*context) for stage, context in stage_contexts(route).items()}


def stage_contexts(route: MaterializedConstructionRealization) -> dict[str, StageContext]:
    """Share exact region ancestry between control assessment and variant projection."""
    architecture = describe_hairpin(route)
    hairpin = architecture.state.molecules[0]
    spans = region_spans(architecture)
    original: list[str | None] = [
        next(name for name, (a, b) in spans.items() if a <= i < b)
        for i in range(len(hairpin.sequence))
    ]
    facts = {"hairpin": (architecture.state.molecules, architecture.state.pairings, [original])}
    if architecture.stage_role == "endpoint":
        facts["endpoint"] = facts["hairpin"]
        return facts
    positions: dict[tuple[str, int], list[str | None]] = defaultdict(list)
    for base in hairpin.lineage:
        positions[(base.origin_id, base.origin_index)].append(original[base.product_index])
    mapped = []
    for strand in route.final_product.strands:
        labels = []
        for base in strand.lineage:
            matches = positions.get((base.origin_id, base.origin_index), [])
            labels.append(matches[0] if len(matches) == 1 else None)
        mapped.append(labels)
    facts["endpoint"] = (route.final_product.strands, route.final_product.pairings, mapped)
    return facts


def _facts(
    strands: tuple[MolecularStrand, ...],
    pairings: tuple[StrandPairObservation, ...],
    regions: list[list[str | None]],
) -> dict[str, Any]:
    chemistry = [[strand.five_prime_end.value, strand.three_prime_end.value] for strand in strands]
    result: dict[str, Any] = {"terminal_chemistry": {"status": "assessed", "value": chemistry}}
    unknown = sum(region is None for labels in regions for region in labels)
    if unknown:
        for prop in ("non_loop_sequences", "non_loop_pairing"):
            result[prop] = {
                "status": "unassessed",
                "reason": "missing_or_ambiguous_region_ancestry",
                "unmapped_positions": unknown,
            }
        return result
    addresses = {}
    sequences = []
    for strand_index, (strand, labels) in enumerate(zip(strands, regions, strict=True)):
        counts: Counter[str] = Counter()
        runs: list[list[str]] = []
        for index, region in enumerate(labels):
            assert region is not None  # Every missing correspondence was handled above.
            if region != "loop":
                addresses[(strand.strand_id, index)] = (strand_index, region, counts[region])
                if not runs or runs[-1][0] != region:
                    runs.append([region, ""])
                runs[-1][1] += strand.sequence[index]
            counts[region] += 1
        sequences.append(runs)
    contacts = []
    for pair in pairings:
        left = addresses.get((pair.left_strand_id, pair.left_index))
        right = addresses.get((pair.right_strand_id, pair.right_index))
        if left is not None and right is not None:
            contacts.append([*min(left, right), *max(left, right), pair.kind.value])
        elif left is not None or right is not None:
            # Do not erase a crossing contact merely because one end is permitted to vary.
            retained = left if left is not None else right
            assert retained is not None
            contacts.append([*retained, "loop", pair.kind.value])
    result.update(
        non_loop_sequences={"status": "assessed", "value": sequences},
        non_loop_pairing={
            "status": "assessed",
            "value": {"positions": sorted(addresses.values()), "contacts": sorted(contacts)},
        },
    )
    return result


def assess_stage_controls(
    controls: tuple[ResolvedStageControl, ...], facts: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    observations = []
    for control in controls:
        values = {name: facts[name][control.stage][control.property] for name in control.members}
        baseline = sorted(values)[0]
        unresolved = {
            name: value for name, value in values.items() if value["status"] != "assessed"
        }
        changed = sorted(
            name
            for name, value in values.items()
            if value.get("value") != values[baseline].get("value")
        )
        status = (
            "unassessed" if unresolved or len(values) < 2 else "different" if changed else "shared"
        )
        observations.append(
            {
                **control.model_dump(mode="json"),
                "status": status,
                "reference_member": baseline,
                "different_members": changed,
                "unassessed_members": unresolved,
                **({"reason": "fewer_than_two_members"} if len(values) < 2 else {}),
            }
        )
    return observations
