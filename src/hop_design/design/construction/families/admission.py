"""Reconcile saved family intent and outcomes with replay-verified molecular authorities."""

import json
from pathlib import Path
from typing import Any

from hop_design.design.source_documents import load_source_mapping

from .choices import FAMILY_INTERPRETATION
from .member_admission import AdmittedMember, _equal, admit_member
from .prepare import prepare_construction_family


def _admit_family(root: Path, depth: int) -> tuple[dict[str, Any], tuple[AdmittedMember, ...]]:
    recorded = load_source_mapping(root / "summary.json", max_bytes=64 * 1024 * 1024)
    if recorded.get("schema") not in {
        "hop.construction-family-result/v1",
        "hop.construction-family-result/v2",
    }:
        raise ValueError("Report requires a supported saved construction-family-result packet.")
    revised = recorded["schema"] == "hop.construction-family-result/v2"
    if revised:
        from .revision import validate_revision

        validate_revision(root, recorded, depth)
    prepared_family = prepare_construction_family(root / "family.json")
    preview = json.loads(prepared_family.json_bytes)
    _equal(recorded.get("interpretation"), FAMILY_INTERPRETATION, "interpretation")
    if not preview["executable"]:
        raise ValueError("Executed family contains conflicting requests.")
    for key in ("family_id", "upper_bounds", "shared_properties", "display_preferences"):
        _equal(recorded.get(key), preview[key], key)
    _equal(
        recorded.get("continuation"), "reconciled" if revised else "sole-witness", "continuation"
    )
    _equal(
        [m["name"] for m in recorded["members"]], [m["name"] for m in preview["members"]], "roster"
    )
    expected_inputs = dict(prepared_family._files)
    admitted = []
    for member, local_preview in zip(recorded["members"], preview["members"], strict=True):
        name = member["name"]
        prefix = f"members/{name}"
        proof = admit_member(
            root / prefix,
            name,
            local_preview,
            {
                leaf: expected_inputs[f"{prefix}/{leaf}"]
                for leaf in ("request.json", "construction.json")
            },
            producer=member["outcome"]["producer"] if revised else recorded["producer"],
            continuation=member["outcome"]["continuation"] if revised else "sole-witness",
            external_design_id=revised,
        )
        _equal(member["outcome"], proof.outcome, f"{name} family outcome")
        admitted.append(proof)
    if revised and recorded["revision"].get("preferred_loop_nt") is not None:
        from ..public import project_hairpin_portrait

        target = next(m for m in admitted if m.name == recorded["revision"]["target_member"])
        if target.receipt is None:
            raise ValueError("A declared preference requires a completed target molecule.")
        for identity in target.receipt.materialized_realization_ids:
            portrait = project_hairpin_portrait(
                target.receipt, materialized_realization_id=identity
            )
            if (
                json.loads(portrait.json_bytes)["loop_nt"]
                != recorded["revision"]["preferred_loop_nt"]
            ):
                raise ValueError("Declared loop preference does not match the selected molecule.")
    return recorded, tuple(admitted)


def admit_family(
    root: Path, *, depth: int = 0
) -> tuple[dict[str, Any], tuple[AdmittedMember, ...]]:
    try:
        return _admit_family(root, depth)
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ValueError("Malformed saved family request/outcome representation.") from error
