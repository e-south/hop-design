"""Capture selected product authorities; a caller-supplied digest is never authority."""

from pathlib import Path
from typing import Any

from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.comparisons.request import (
    ComparisonRequest,
    GroupedComparisonBrief,
    StageComparisonBrief,
)
from hop_design.serialization import canonical_json_bytes

from ..complete.bundle import load_verified_construction_bundle
from ..discovery.molecules import molecular_identities
from ..selection_reference import load_construction_selection
from .prior_materials import capture_prior_materials


def capture_references(
    brief: ComparisonRequest, directory: Path
) -> tuple[ComparisonRequest, dict[str, Any], dict[str, bytes], tuple[ProtectedRoot, ...]]:
    if not isinstance(brief, (GroupedComparisonBrief, StageComparisonBrief)):
        return brief, {}, {}, ()
    content = brief.model_dump(mode="json", by_alias=True)
    references: dict[str, Any] = {}
    files: dict[str, bytes] = {}
    roots: list[ProtectedRoot] = []
    for group, value in zip(brief.groups, content["groups"], strict=True):
        ref = group.product_reference
        if ref is None:
            continue
        bundle_root = ProtectedRoot.capture(directory / ref.bundle_path)
        selection_root = ProtectedRoot.capture(directory / ref.selection_path)
        receipt = load_verified_construction_bundle(bundle_root.path)
        selection = load_construction_selection(selection_root.path, receipt=receipt)
        bundle_root.require_unchanged()
        selection_root.require_unchanged()
        roots.extend((bundle_root, selection_root))
        prefix = f"references/{group.name}"
        bundle_path = f"{prefix}/construction"
        selection_path = f"{prefix}/selection.json"
        files[f"{bundle_path}/construction-bundle.json"] = canonical_json_bytes(receipt._bundle)
        files.update({f"{bundle_path}/{k}": data for k, data in receipt._artifacts.items()})
        files[selection_path] = selection.json_bytes
        value["product_reference"].update(bundle_path=bundle_path, selection_path=selection_path)
        references[group.name] = {
            "stage": ref.stage,
            "molecular_identity": molecular_identities(
                receipt, selection.materialized_realization_id
            )[ref.stage],
            "source_result_id": receipt.result_id,
            "materialized_realization_id": selection.materialized_realization_id,
        }
    if isinstance(brief, StageComparisonBrief) and brief.reuse_prior_materials is not None:
        portable, prior, material_files, material_roots = capture_prior_materials(
            brief.reuse_prior_materials, directory
        )
        content["reuse_prior_materials"] = portable.model_dump(mode="json")
        references["@prior_materials"] = prior
        files.update(material_files)
        roots.extend(material_roots)
    return (
        type(brief).model_validate_json(canonical_json_bytes(content)),
        references,
        files,
        tuple(roots),
    )


def reference_summary(references: dict[str, Any] | None) -> dict[str, Any]:
    if not references:
        return {}
    products = {key: value for key, value in references.items() if key != "@prior_materials"}
    return {
        **({"product_references": products} if products else {}),
        **(
            {"prior_material_reference": references["@prior_materials"]}
            if "@prior_materials" in references
            else {}
        ),
    }
