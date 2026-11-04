"""Preview every named family member and its effective domain before any search."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.construction.scaffold.family_preview import render_family_preview
from hop_design.models.construction.family.request import (
    ConstructionFamilyRequest,
    ScaffoldFamilyMember,
)
from hop_design.models.construction.payload import _content_id
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.source import _contains_internal_schema_name
from hop_design.serialization import canonical_json_bytes

from .conflicts import DIMENSIONS, member_conflicts
from .intent import comparison_intent, render_comparison_intent
from .packet import FamilyPacket


@dataclass(frozen=True, init=False, repr=False)
class PreparedConstructionFamily(FamilyPacket):
    """Expanded intent and conflicts, without a molecular feasibility claim."""


def load_family_request(path: str | Path) -> tuple[ConstructionFamilyRequest, bytes]:
    mapping = load_source_mapping(path)
    if _contains_internal_schema_name(mapping):
        raise ValueError("Family inputs must use external 'schema' fields.")
    request = ConstructionFamilyRequest.model_validate_json(json.dumps(mapping))
    return request, canonical_json_bytes(mapping)


def expand_member(
    family: ConstructionFamilyRequest, member: ScaffoldFamilyMember, authored_base: dict[str, Any]
) -> tuple[dict[str, Any], ProductRequest]:
    conflicts = member_conflicts(family, member)
    if conflicts:
        raise ValueError(" ".join(c["message"] for c in conflicts))
    data = deepcopy(authored_base)
    scaffold = data["whole_route_constraints"].get("hairpin_scaffold") or {}
    for dimension, local_name in DIMENSIONS:
        value = getattr(member, dimension)
        if value is None:
            continue
        data["foldback"]["geometry"][local_name] = [value]
        scaffold[dimension] = {"minimum": value, "maximum": value}
    data["whole_route_constraints"]["hairpin_scaffold"] = scaffold
    expanded = ProductRequest.model_validate_json(json.dumps(data))
    expanded.construction_source()
    return data, expanded


def prepare_construction_family(path: str | Path) -> PreparedConstructionFamily:
    """Expand a finite roster, preserving contradictions instead of relaxing intent."""
    family, authored = load_family_request(path)
    base = json.loads(authored)["base_request"]
    files = {"family.json": authored}
    members: list[dict[str, Any]] = []
    seen = set()
    for member in family.members:
        row: dict[str, Any] = {
            "name": member.name,
            "requested_variation": member.model_dump(mode="json", exclude={"name"}),
            "conflicts": member_conflicts(family, member),
        }
        try:
            request, validated = expand_member(family, member, base)
            content = canonical_json_bytes(request)
            if content in seen:
                raise ValueError("This member duplicates an effective product request.")
            seen.add(content)
            source = validated.construction_source()
            files[f"members/{member.name}/request.json"] = content
            files[f"members/{member.name}/construction.json"] = canonical_json_bytes(source)
            row.update(
                conflict=None,
                effective_geometry=source.foldback.geometry_domain.model_dump(mode="json"),
            )
        except ValueError as error:
            row["conflict"] = str(error)
        members.append(row)
    jobs = (family.base_request.foldback, family.base_request.basal)
    summary: dict[str, Any] = {
        "schema": "hop.construction-family-preview/v3",
        "comparison_intent": comparison_intent(family),
        "family_id": _content_id("construction-family", 1, json.loads(authored)),
        "executable": all(row["conflict"] is None for row in members),
        "members": members,
        "shared_properties": list(family.shared_properties),
        "display_preferences": [p.model_dump(mode="json") for p in family.display_preferences],
        "upper_bounds": {
            "members": len(members),
            "search_nodes": len(members)
            * sum(j.search.max_search_nodes for j in jobs if j is not None),
            "selected_pair_continuations": len(members),
            "composition_combinations": len(members)
            * family.base_request.enumeration.max_combinations,
        },
    }
    report = [
        "# Preview a scaffold family",
        "",
        "Named members narrow the authored domains. No molecular search has run.",
        "[Dimensioned request preview](preview.svg)",
        "",
        *render_comparison_intent(family),
    ]
    for row in members:
        report.append(
            f"- {row['name']}: "
            + (
                f"conflict — {row['conflict']}"
                if row["conflict"]
                else "ready for bounded execution"
            )
        )
        variation = row["requested_variation"]
        for conflict in row["conflicts"]:
            report.append(
                f"  Declaration: `{conflict['declaration_path']}` = {conflict['declared']}"
            )
            report.extend("  Explicit option: " + edit for edit in conflict["edit_options"])
        loop = "base domain" if variation["loop_nt"] is None else f"{variation['loop_nt']} nt"
        extension = (
            "base domain"
            if variation["loop_side_paired_bp"] is None
            else f"{variation['loop_side_paired_bp']} bp"
        )
        report.append(f"  {row['name']}: loop {loop}; loop-side extension {extension}")
        report.append(
            "  Effective geometry: " + json.dumps(row.get("effective_geometry"), sort_keys=True)
        )
    report += [
        "",
        "Finite bounds: " + json.dumps(summary["upper_bounds"], sort_keys=True),
        (
            "A complete member is a modeled preparation; a family is not a "
            "pooled reaction. Display preferences never relax requirements."
        ),
        "",
    ]
    files["preview.svg"] = render_family_preview(summary)
    return PreparedConstructionFamily._create(files, summary, "\n".join(report))
