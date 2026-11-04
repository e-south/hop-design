"""Sequence views and print figures rebuilt from verified complete molecular authorities."""

from pathlib import Path
from typing import Any

from hop_design.export.construction.molecular.folded_sequence import render_folded_sequence
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection
from hop_design.serialization import canonical_json_bytes

from ..projections.folded_sequence import folded_sequence_view
from ..public import VerifiedConstructionBundle, load_verified_construction_bundle


def sequence_drawings(
    root: Path,
    native: dict[str, Any],
    receipts: dict[str, VerifiedConstructionBundle] | None = None,
) -> tuple[dict[str, bytes], list[bytes]]:
    files: dict[str, bytes] = {}
    pages: list[bytes] = []
    rows = []
    for option in native["options"]:
        receipt = (
            load_verified_construction_bundle(root / option["selection"]["bundle_path"])
            if receipts is None
            else receipts[option["label"]]
        )
        route = next(
            r
            for r in receipt._verified_source().result.realizations
            if r.materialized_realization_id == option["materialized_realization_id"]
        )
        portrait = HairpinPortraitProjection.model_validate_json(
            (root / Path(option["portrait"]).with_suffix(".json")).read_bytes()
        )
        source = receipt._verified_source().result
        catalog = source.foldback_authority.neighborhood.request.enzyme_provisioning.catalog
        names = {enzyme.enzyme_id: enzyme.canonical_name for enzyme in catalog.enzymes}
        facts = option.get("target_facts", {})
        methods = " · ".join(
            f"{role}: {names[facts[key]]}"
            for role, key in (("Nick", "basal_nick_enzyme_id"), ("Release", "release_enzyme_id"))
            if facts.get(key) is not None
        )
        rows.append((option, portrait, route.final_product, methods))
    if not rows:
        return files, pages
    ref, reference, endpoint, _ = rows[0]
    for ordinal, (option, portrait, product, methods) in enumerate(rows, 1):
        view = folded_sequence_view(
            portrait,
            reference,
            label=option["label"],
            reference_label=ref["label"],
            materials=option["material_roles"],
            reference_materials=ref["material_roles"],
            endpoint=product,
            reference_endpoint=endpoint,
        )
        svg = render_folded_sequence(
            view, display_label=f"Design {ordinal}", reference_label="Design 1", methods=methods
        )
        files[f"views/{option['label']}.json"] = canonical_json_bytes(view)
        files[f"views/{option['label']}.svg"] = svg
        pages.append(svg)
    return files, pages
