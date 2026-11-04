"""Check required stems, flanks and materials using the existing construction-set owner."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hop_design.models.construction.family.selection import ConstructionSetRequest
from hop_design.models.construction.intents.family import DesignFamilySelection
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ...complete.bundle import load_verified_construction_bundle
from ...families.selection import ConstructionSet, _select_admitted_construction_set
from ...intents.base import Source
from ...intents.comparisons import source_value
from ...intents.inserts.retrieve import InsertSetHandoff
from ...selection_reference import select_construction_realization

if TYPE_CHECKING:
    from .choices import DesignFamilyChoices


def assemble(
    choices: DesignFamilyChoices, members: dict[str, dict[str, Any]], baseline: str
) -> ConstructionSet:
    if set(members) != {m["name"] for m in choices.resolution["members"]}:
        raise ValueError("Select exactly one preparation for every required member.")
    if baseline not in members:
        raise ValueError("The baseline must name an explicitly selected member.")
    with tempfile.TemporaryDirectory(prefix="hop-exact-family-") as temporary:
        root = Path(temporary)
        records, roster = {}, []
        for name, selected in sorted(members.items()):
            owner = choices.member(name)
            destination = root / name
            owner.retrieve(selected, destination)
            native = (
                destination
                if owner.resolution["intent"]["product"] == "released_insert"
                else destination / "members/selected"
            )
            receipt = load_verified_construction_bundle(native / "construction")
            identity = selected["materialized_realization_id"]
            exact = select_construction_realization(receipt, materialized_realization_id=identity)
            exact.write(root / f"{name}.json")
            records[name] = receipt
            roster.append(
                {
                    "name": name,
                    "bundle_path": str(native / "construction"),
                    "selection_path": f"{name}.json",
                }
            )
        value = {
            "schema": "hop.construction-set/v2",
            "members": roster,
            "baseline": baseline,
            "shared_properties": choices.resolution["shared_properties"],
            "compared_properties": [],
        }
        if choices.resolution["shared_material_roles"]:
            reference = next(m for m in roster if m["name"] == baseline)
            value["reuse_prior_materials"] = {
                "reference": {k: v for k, v in reference.items() if k != "name"},
                "roles": choices.resolution["shared_material_roles"],
            }
        request = ConstructionSetRequest.model_validate_json(canonical_json_bytes(value))
        packet = _select_admitted_construction_set(root / "set.json", request, records, ())
    object.__setattr__(packet, "_roots", ())
    return choices._protect(packet)


def select_members(
    choices: DesignFamilyChoices, members: dict[str, dict[str, Any]], *, baseline: str
) -> dict[str, Any]:
    assemble(choices, members, baseline)
    value = {
        "schema": "hop.design-family-selection/v1",
        "request_digest": choices.resolution["request_digest"],
        "members": members,
        "baseline": baseline,
    }
    value["selection_digest"] = sha256_digest(canonical_json_bytes(value))
    return DesignFamilySelection.model_validate_json(canonical_json_bytes(value)).model_dump(
        mode="json", by_alias=True
    )


def retrieve_family(
    choices: DesignFamilyChoices, source: Source, destination: str | Path
) -> InsertSetHandoff:
    selected = DesignFamilySelection.model_validate_json(canonical_json_bytes(source_value(source)))
    body = selected.model_dump(mode="json", by_alias=True, exclude={"selection_digest"})
    if (
        selected.request_digest != choices.resolution["request_digest"]
        or sha256_digest(canonical_json_bytes(body)) != selected.selection_digest
    ):
        raise ValueError("Family selection or membership disagrees with its saved request.")
    output = choices._output(destination)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to replace family handoff: {output}")
    packet = assemble(choices, selected.members, selected.baseline)
    summary = json.loads(packet.json_bytes)
    packet = ConstructionSet._create(
        {
            **dict(packet._files),
            "design-selection.json": canonical_json_bytes(selected),
            "family-request.json": canonical_json_bytes(choices.resolution["intent"]),
        },
        summary,
        packet.report_text,
    )
    object.__setattr__(packet, "_roots", ())
    choices._protect(packet).write(output)
    return InsertSetHandoff(
        output, tuple(m["materialized_realization_id"] for m in summary["members"])
    )
