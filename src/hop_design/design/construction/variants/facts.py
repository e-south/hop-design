"""Project neighborhood membership from complete, stage-qualified molecular states."""

import json
from pathlib import Path
from typing import Any

from hop_design.models.construction.complete.product import MaterializedFinalProduct
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection
from hop_design.models.construction.projections.neighborhoods import NEIGHBORHOOD_REGIONS
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..comparisons.controls import StageContext, stage_contexts, stage_facts
from ..projections.interfaces import preparation_interface
from ..projections.product_stages import project_product_stages
from ..projections.trajectory import project_complete_construction_trajectory
from ..public import VerifiedConstructionBundle
from .parameters.facts import parameter_facts


def _regions(
    context: StageContext,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]] | None:
    strands, pairs, labels = context
    if any(region is None for strand_labels in labels for region in strand_labels):
        return None
    addresses: dict[tuple[str, int], list[Any]] = {}
    sequences: list[dict[str, Any]] = []
    terminals: list[dict[str, Any]] = []
    for si, (strand, strand_labels) in enumerate(zip(strands, labels, strict=True)):
        offsets: dict[str, int] = {}
        runs: list[dict[str, Any]] = []
        for index, region in enumerate(strand_labels):
            assert region is not None
            offset = offsets.get(region, 0)
            addresses[strand.strand_id, index] = [si, region, offset]
            offsets[region] = offset + 1
            if not runs or runs[-1]["region"] != region:
                runs.append({"strand": si, "region": region, "sequence": ""})
            runs[-1]["sequence"] += strand.sequence[index]
        sequences.extend(runs)
        if strand_labels:
            terminals.extend(
                [
                    {
                        "strand": si,
                        "region": strand_labels[0],
                        "end": "five_prime",
                        "chemistry": strand.five_prime_end.value,
                    },
                    {
                        "strand": si,
                        "region": strand_labels[-1],
                        "end": "three_prime",
                        "chemistry": strand.three_prime_end.value,
                    },
                ]
            )
    contacts = []
    for pair in pairs:
        ends = sorted(
            (
                addresses[pair.left_strand_id, pair.left_index],
                addresses[pair.right_strand_id, pair.right_index],
            )
        )
        contacts.append({"left": ends[0], "right": ends[1], "kind": pair.kind.value})
    return sequences, sorted(contacts, key=canonical_json_bytes), terminals


def _variants(
    stage: str, context: StageContext, endpoint: MaterializedFinalProduct
) -> dict[str, dict[str, Any] | None]:
    regional = _regions(context)
    result: dict[str, dict[str, Any] | None] = {}
    for neighborhood, names in NEIGHBORHOOD_REGIONS.items():
        if neighborhood == "interfaces":
            ends = endpoint.cohesive_ends if stage == "endpoint" else ()
            content = {
                "stage": stage,
                "neighborhood": neighborhood,
                "sequences": [
                    {
                        "product_end": e.product_end,
                        "sequence": e.sequence,
                        "overhang_end": e.overhang_end.value,
                        "strand": next(
                            i
                            for i, s in enumerate(endpoint.strands)
                            if s.strand_id == e.protruding_strand_id
                        ),
                    }
                    for e in ends
                ],
                "contacts": [],
                "terminals": [],
            }
        elif regional is None:
            result[neighborhood] = None
            continue
        else:
            sequences, contacts, terminals = regional
            content = {
                "stage": stage,
                "neighborhood": neighborhood,
                "sequences": [s for s in sequences if s["region"] in names],
                "contacts": [
                    p for p in contacts if p["left"][1] in names or p["right"][1] in names
                ],
                "terminals": [t for t in terminals if t["region"] in names],
            }
        result[neighborhood] = {
            "variant_id": sha256_digest(canonical_json_bytes(content)),
            **content,
        }
    return result


def regional_variants(route: MaterializedConstructionRealization) -> dict[str, Any]:
    """One regional identity authority for every admitted complete route."""
    return {
        stage: _variants(stage, context, route.final_product)
        for stage, context in stage_contexts(route).items()
    }


def option_facts(
    root: Path, native: dict[str, Any], receipts: dict[str, VerifiedConstructionBundle]
) -> list[dict[str, Any]]:
    options = []
    for option in native["options"]:
        receipt = receipts[option["label"]]
        route = next(
            r
            for r in receipt._verified_source().result.realizations
            if r.materialized_realization_id == option["materialized_realization_id"]
        )
        portrait = HairpinPortraitProjection.model_validate_json(
            (root / option["portrait"]).with_suffix(".json").read_bytes()
        )
        stages = project_product_stages(
            portrait,
            project_complete_construction_trajectory(
                receipt._verified_source(),
                materialized_realization_id=option["materialized_realization_id"],
            ),
        )
        method = next(b for b in native["branches"] if b["branch_id"] == option["branch_id"])
        branch_request = json.loads((root / method["request"]).read_bytes())
        options.append(
            {
                **option,
                "loop_sequence": portrait.state.molecules[0].sequence[
                    portrait.loop_span.start.offset : portrait.loop_span.end.offset
                ],
                "release_enzyme_id": method["release_enzyme_id"],
                "release_method": method["release_method"],
                **preparation_interface(route, branch_request),
                "parameter_values": parameter_facts(route, branch_request),
                "portrait_data": json.loads(canonical_json_bytes(portrait)),
                "endpoint_data": json.loads(canonical_json_bytes(route.final_product)),
                "stages_data": json.loads(canonical_json_bytes(stages)),
                "stage_facts": stage_facts(route),
                "variants": regional_variants(route),
            }
        )
    return options
