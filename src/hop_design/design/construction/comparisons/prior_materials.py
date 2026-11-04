"""Capture one verified preparation and its exact external materials for explicit reuse."""

from pathlib import Path
from typing import Any

from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.comparisons.materials import PriorMaterialReuse
from hop_design.models.construction.complete.basal_embedding import basal_source_offset
from hop_design.models.construction.complete.evaluation_inputs import replay_linear_source_embedding
from hop_design.models.construction.complete.pcr.authority import PrimerExtensionAuthority
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.projections.materials import external_material_uses
from hop_design.serialization import canonical_json_bytes

from ..complete.bundle import load_verified_construction_bundle
from ..selection_reference import load_construction_selection


def material_facts(route: MaterializedConstructionRealization) -> dict[str, Any]:
    materials = {
        use.role.value: material.model_dump(mode="json")
        for material, use in external_material_uses(route)
    }
    policies = {
        role: {"mode": "fixed", "material": material}
        for role, material in materials.items()
        if "primer" not in role
    }
    source = route.source_preparation
    for role, primer in (
        ("source_materialization_forward_primer", source.forward_primer),
        ("source_materialization_reverse_primer", source.reverse_primer),
    ):
        policies[role] = {"mode": "fixed", "primer": primer.model_dump(mode="json")}
    for transition in route.construction_program.transitions:
        pcr = transition.pcr_authority
        if isinstance(pcr, PrimerExtensionAuthority):
            for use, primer in (
                (pcr.forward_primer_use, pcr.forward_primer),
                (pcr.reverse_primer_use, pcr.reverse_primer),
            ):
                if use.role.value in materials:
                    policies[use.role.value] = {
                        "mode": "fixed",
                        "primer": primer.model_dump(mode="json"),
                    }
    context = None
    if route.basal_authority is not None:
        top, bottom = source.product_state.molecules
        prefix, _, _ = replay_linear_source_embedding(
            foldback=route.foldback_authority,
            source_sequence=top.sequence,
            complement_sequence=bottom.sequence,
        )
        context = prefix[: basal_source_offset(route.basal_authority, prefix)]
    return {"materials": materials, "fixed_policies": policies, "source_context": context}


def capture_prior_materials(
    declaration: PriorMaterialReuse, directory: Path
) -> tuple[PriorMaterialReuse, dict[str, Any], dict[str, bytes], tuple[ProtectedRoot, ...]]:
    ref = declaration.reference
    bundle_root = ProtectedRoot.capture(directory / ref.bundle_path)
    selection_root = ProtectedRoot.capture(directory / ref.selection_path)
    receipt = load_verified_construction_bundle(bundle_root.path)
    selection = load_construction_selection(selection_root.path, receipt=receipt)
    bundle_root.require_unchanged()
    selection_root.require_unchanged()
    route = next(
        r
        for r in receipt._verified_source().result.realizations
        if r.materialized_realization_id == selection.materialized_realization_id
    )
    bundle_path, selection_path = (
        "material-reference/construction",
        "material-reference/selection.json",
    )
    files = {
        f"{bundle_path}/construction-bundle.json": canonical_json_bytes(receipt._bundle),
        selection_path: selection.json_bytes,
    }
    files.update({f"{bundle_path}/{k}": v for k, v in receipt._artifacts.items()})
    portable = PriorMaterialReuse.model_validate_json(
        canonical_json_bytes(
            {
                "reference": {"bundle_path": bundle_path, "selection_path": selection_path},
                "roles": declaration.roles,
            }
        )
    )
    facts = {
        "source_result_id": receipt.result_id,
        "materialized_realization_id": selection.materialized_realization_id,
        "required_roles": list(declaration.roles),
        **material_facts(route),
    }
    return portable, facts, files, (bundle_root, selection_root)


def prior_material_changes(prior: dict[str, Any], materials: dict[str, Any]) -> dict[str, Any]:
    roles = sorted(set(prior["materials"]) | set(materials))
    return {
        "reference_realization_id": prior["materialized_realization_id"],
        "changed_roles": [
            role
            for role in roles
            if prior["materials"].get(role, {}).get("material_id")
            != materials.get(role, {}).get("material_id")
        ],
        "reused_roles": [
            role
            for role in roles
            if prior["materials"].get(role, {}).get("material_id")
            == materials.get(role, {}).get("material_id")
        ],
    }
