"""Verify explicit set membership before creating a portable preparation packet."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.construction.comparisons.controls import (
    prior_material_lines,
    stage_control_lines,
)
from hop_design.export.construction.handoff.material_set import render_set_materials
from hop_design.export.construction.scaffold.report_pdf import render_report_pdf
from hop_design.export.construction.scaffold.terminal_plate import terminal_plates
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.comparisons.materials import PriorMaterialReuse
from hop_design.models.construction.family.selection import ConstructionSetRequest
from hop_design.models.construction.payload import _content_id
from hop_design.models.construction.source import _contains_internal_schema_name
from hop_design.serialization import canonical_json_bytes

from ..comparison import project_construction_comparison
from ..comparisons.controls import assess_stage_controls, stage_facts
from ..comparisons.prior_materials import (
    capture_prior_materials,
    material_facts,
    prior_material_changes,
)
from ..complete.bundle import VerifiedConstructionBundle
from ..discovery.molecules import preparation_materials
from .controls import assess_controls
from .packet import SourceBoundFamilyPacket
from .properties import MOLECULAR_CONTROLS, shared_values
from .set_members import SelectedSetMember, admit_set_members, project_set_members

type _PriorMaterials = (
    tuple[PriorMaterialReuse, dict[str, Any], dict[str, bytes], tuple[ProtectedRoot, ...]] | None
)


def _capture_prior(request: ConstructionSetRequest, directory: Path) -> _PriorMaterials:
    if request.reuse_prior_materials is None:
        return None
    return capture_prior_materials(request.reuse_prior_materials, directory)


@dataclass(frozen=True, init=False, repr=False)
class ConstructionSet(SourceBoundFamilyPacket):
    """Explicit complete members, molecular differences and consolidated order specifications."""

    _packet_schema: ClassVar[str] = "hop.construction-set-packet/v1"


def select_construction_set(path: str | Path) -> ConstructionSet:
    """Select exact accepted identities; never infer membership from display order."""
    path = Path(path)
    mapping = load_source_mapping(path)
    if _contains_internal_schema_name(mapping):
        raise ValueError("Set requests must use external 'schema' fields.")
    request = ConstructionSetRequest.model_validate_json(json.dumps(mapping))
    prior = _capture_prior(request, path.parent)
    records, roots = admit_set_members(request, path.parent)
    return _assemble_construction_set(request, records, roots, prior)


def _select_admitted_construction_set(
    path: Path,
    request: ConstructionSetRequest,
    receipts: dict[str, VerifiedConstructionBundle],
    input_roots: tuple[ProtectedRoot, ...],
) -> ConstructionSet:
    """Assemble explicit members from this invocation's already admitted authorities."""
    prior = _capture_prior(request, path.parent)
    records = project_set_members(request, path.parent, receipts)
    return _assemble_construction_set(request, records, input_roots, prior)


def _assemble_construction_set(
    request: ConstructionSetRequest,
    records: dict[str, SelectedSetMember],
    input_roots: tuple[ProtectedRoot, ...],
    prior_materials: _PriorMaterials,
) -> ConstructionSet:
    """Check comparison controls and package exact, bound member projections."""
    roots = list(input_roots)
    prior = None
    portable_prior = None
    material_files: dict[str, bytes] = {}
    if prior_materials is not None:
        portable_prior, prior, material_files, material_roots = prior_materials
        roots.extend(material_roots)
    reference = records[request.baseline]
    stage_observations = assess_stage_controls(
        request.stage_controls,
        {
            name: stage_facts(
                next(
                    route
                    for route in receipt._verified_source().result.realizations
                    if route.materialized_realization_id == selection.materialized_realization_id
                )
            )
            for name, (receipt, selection, _, _) in records.items()
        }
        if request.stage_controls
        else {},
    )
    if any(c["status"] != "shared" for c in stage_observations):
        raise ValueError(
            f"Stage-qualified controls are not verified as shared: {stage_observations}"
        )
    reference_values = shared_values(reference.projection, request.shared_properties)
    control_values = {
        name: shared_values(record.projection, (*MOLECULAR_CONTROLS, *request.shared_properties))
        for name, record in records.items()
    }
    controls = assess_controls(control_values, request.baseline, request.shared_properties)
    files = dict(material_files)
    prior_changes = {}
    members: list[dict[str, Any]] = []
    inventory = []
    portable_members = []
    with tempfile.TemporaryDirectory(prefix="hop-set-") as temporary:
        for member in request.members:
            receipt, selection, portrait, projection = records[member.name]
            values = shared_values(projection, request.shared_properties)
            if (projection["state"]["phase"], projection["endpoint"]) != (
                reference.projection["state"]["phase"],
                reference.projection["endpoint"],
            ):
                raise ValueError(
                    "Comparative members must represent the same product stage and endpoint."
                )
            conflicts = [
                key for key in request.shared_properties if values[key] != reference_values[key]
            ]
            if conflicts:
                raise ValueError(
                    f"Set member {member.name} contradicts shared properties: {conflicts}."
                )
            prefix = f"members/{member.name}"
            portrait_path = Path(temporary) / member.name
            portrait.write(portrait_path)
            for file in portrait_path.rglob("*"):
                if file.is_file():
                    files[f"{prefix}/portrait/{file.relative_to(portrait_path).as_posix()}"] = (
                        file.read_bytes()
                    )
            # Copy the admitted immutable authority snapshot, never reread mutable source paths.
            files[f"{prefix}/construction/construction-bundle.json"] = canonical_json_bytes(
                receipt._bundle
            )
            files.update(
                {
                    f"{prefix}/construction/{name}": content
                    for name, content in receipt._artifacts.items()
                }
            )
            if member.name != request.baseline:
                comparison = project_construction_comparison(
                    reference.receipt,
                    receipt,
                    left_realization_id=reference.selection.materialized_realization_id,
                    right_realization_id=selection.materialized_realization_id,
                )
                files[f"comparisons/{member.name}.json"] = comparison.json_bytes
            realization = next(
                r
                for r in receipt._verified_source().result.realizations
                if r.materialized_realization_id == selection.materialized_realization_id
            )
            inventory.append((member.name, realization))
            if prior is not None:
                materials = material_facts(realization)["materials"]
                differences = prior_material_changes(prior, materials)
                required = set(prior["required_roles"])
                if not required <= set(differences["reused_roles"]):
                    raise ValueError(
                        f"Member {member.name} does not reuse the required prior materials."
                    )
                prior_changes[member.name] = differences
            members.append(
                {
                    "name": member.name,
                    "source_result_id": receipt.result_id,
                    "materialized_realization_id": selection.materialized_realization_id,
                    "properties": values,
                    "stage": projection["state"]["phase"],
                    "preparation": f"{prefix}/portrait/preparation/report.md",
                }
            )
            portable_members.append(
                {
                    "name": member.name,
                    "bundle_path": f"{prefix}/construction",
                    "selection_path": f"{prefix}/portrait/selection.json",
                }
            )
    identity_body = {
        "baseline": request.baseline,
        "members": members,
        "shared_properties": list(request.shared_properties),
        "compared_properties": list(request.compared_properties),
        "comparison_controls": [c.model_dump(mode="json") for c in controls],
        **(
            {"prior_material_reference": prior, "prior_material_changes": prior_changes}
            if prior is not None
            else {}
        ),
        **({"stage_controls": stage_observations} if request.stage_controls else {}),
    }
    summary: dict[str, object] = {
        "schema": "hop.construction-set-summary/v2",
        "set_id": _content_id("construction-set", 2, identity_body),
        **identity_body,
    }
    files.update(render_set_materials(tuple(inventory)))
    files["set.json"] = canonical_json_bytes(
        {
            **request.model_dump(mode="json", by_alias=True),
            "members": portable_members,
            **(
                {"reuse_prior_materials": portable_prior.model_dump(mode="json")}
                if portable_prior is not None
                else {}
            ),
        }
    )
    terminal_dimensions = {"five_prime_unpaired_nt", "three_prime_unpaired_nt"}
    if terminal_dimensions.intersection(
        (*request.compared_properties, *request.shared_properties)
    ) and all(member["properties"]["endpoint"] == "adapter_ligated_hairpin" for member in members):
        options = [
            {
                "label": member["name"],
                "portrait": f"members/{member['name']}/portrait/projection.svg",
                "material_roles": preparation_materials(
                    records[member["name"]].receipt, member["materialized_realization_id"]
                ),
            }
            for member in members
        ]
        pages = terminal_plates({"options": options, "baseline": request.baseline}, files)
        files.update({f"pages/terminal-forms-{i + 1}.svg": p for i, p in enumerate(pages)})
        files["report.pdf"] = render_report_pdf(tuple(pages))
    report = "\n".join(
        [
            "# Selected scaffold set",
            "",
            "Explicit membership: " + ", ".join(m["name"] for m in members),
            "",
            (
                "Single selected molecule; between-member agreement is not assessed."
                if len(members) == 1
                else "Shared controls are checked across the explicitly selected molecules."
            ),
            "",
            "Shared: " + ", ".join(request.shared_properties),
            "Compared: " + ", ".join(request.compared_properties),
            *stage_control_lines(summary),
            *prior_material_lines(summary),
            "",
            (
                "Inspect comparisons for accompanying sequence, material, contact "
                "and product changes. This set does not isolate a causal effect."
            ),
            "",
            (
                "oligos.csv consolidates sequence and terminal chemistry. "
                "oligo-uses.csv retains each member and role."
            ),
            (
                "Each member has its own preparation and unresolved reaction "
                "prerequisites. No pooled reaction or experimental performance is established."
            ),
            "",
        ]
    )
    packet = ConstructionSet._create(files, summary, report)
    object.__setattr__(packet, "_roots", tuple(roots))
    return packet
