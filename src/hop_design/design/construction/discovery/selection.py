"""Retrieve user-named preparations from replay-verified discovery options."""

import json
from pathlib import Path
from typing import Any

from hop_design.export.construction.scaffold.discovery_plate import discovery_plates
from hop_design.export.construction.scaffold.options_report import selected_plate
from hop_design.export.construction.scaffold.report_pdf import render_report_pdf
from hop_design.export.construction.scaffold.terminal_plate import terminal_plates
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.comparisons.materials import PriorMaterialReuse
from hop_design.models.construction.family.selection import ConstructionSetRequest
from hop_design.models.construction.stage_controls import ResolvedStageControl
from hop_design.serialization import canonical_json_bytes

from ..families.selection import ConstructionSet, _select_admitted_construction_set
from ..options.drawings import complementary_drawings
from ..public import VerifiedConstructionBundle
from .admission import captured_discovery
from .molecules import stage_groups


def select_scaffold_options(
    path: str | Path,
    *,
    members: dict[str, str],
    baseline: str,
    shared_properties: tuple[str, ...] = (),
    compared_properties: tuple[str, ...] = (),
    stage_controls: tuple[ResolvedStageControl, ...] = (),
    reuse_prior_materials: PriorMaterialReuse | None = None,
) -> ConstructionSet:
    """Bind user names to explicit option labels without selecting a default preparation."""
    _require_members(members, baseline)
    with captured_discovery(path) as captured:
        return _select_captured_scaffold_options(
            *captured,
            members=members,
            baseline=baseline,
            shared_properties=shared_properties,
            compared_properties=compared_properties,
            stage_controls=stage_controls,
            reuse_prior_materials=reuse_prior_materials,
        )


def _require_members(members: dict[str, str], baseline: str) -> None:
    if not members or len(members) > 64 or baseline not in members:
        raise ValueError("Select 1-64 named members and an explicit baseline member name.")


def _select_captured_scaffold_options(
    root: Path,
    pool: dict[str, Any],
    receipts: dict[str, VerifiedConstructionBundle],
    protected: ProtectedRoot,
    *,
    members: dict[str, str],
    baseline: str,
    shared_properties: tuple[str, ...] = (),
    compared_properties: tuple[str, ...] = (),
    stage_controls: tuple[ResolvedStageControl, ...] = (),
    reuse_prior_materials: PriorMaterialReuse | None = None,
) -> ConstructionSet:
    """Retrieve inside the live captured-discovery scope that already admitted this pool."""
    _require_members(members, baseline)
    options = {option["label"]: option for option in pool["options"]}
    missing = set(members.values()) - options.keys()
    if missing:
        raise ValueError(f"Unknown option labels: {sorted(missing)}.")
    request = {
        "schema": "hop.construction-set/v2"
        if stage_controls or reuse_prior_materials
        else "hop.construction-set/v1",
        **(
            {"reuse_prior_materials": reuse_prior_materials.model_dump(mode="json")}
            if reuse_prior_materials is not None
            else {}
        ),
        **(
            {"stage_controls": [c.model_dump(mode="json") for c in stage_controls]}
            if stage_controls
            else {}
        ),
        "members": [
            {"name": name, **options[label]["selection"]} for name, label in members.items()
        ],
        "baseline": baseline,
        "shared_properties": list(shared_properties),
        "compared_properties": list(compared_properties),
    }
    request_path = root / "selection.json"
    request_path.write_bytes(canonical_json_bytes(request))
    selected = _select_admitted_construction_set(
        request_path,
        ConstructionSetRequest.model_validate_json(json.dumps(request)),
        {name: receipts[label] for name, label in members.items()},
        (protected,),
    )
    files = dict(selected._files)
    for name, label in members.items():
        prefix = f"members/{name}/portrait"
        for leaf, content in complementary_drawings(
            receipts[label],
            options[label]["materialized_realization_id"],
            files[f"{prefix}/projection.json"],
            files[f"{prefix}/projection.svg"],
        ).items():
            files[f"{prefix}/{leaf}"] = content
    context = json.loads((root / "intent/request.json").read_bytes())["product"]
    summary = json.loads(selected.json_bytes)
    files.update(selected_plate(summary, files, context=context))
    files["discovery-selection.json"] = canonical_json_bytes(
        {
            "request_digest": pool["request_digest"],
            "comparison_stage": pool["comparison_stage"],
            "members": members,
            "baseline": baseline,
        }
    )
    named_options = [
        {
            **{
                key: options[label][key]
                for key in (
                    "geometry",
                    "material_roles",
                    "molecular_identity",
                    "materialized_realization_id",
                    "branch_id",
                )
            },
            "label": name,
            "source_option_label": label,
            "portrait": f"members/{name}/portrait/projection.svg",
            "preparation": f"members/{name}/portrait/preparation/report.md",
            "product_stages": f"members/{name}/portrait/stages.svg",
        }
        for name, label in members.items()
    ]
    groups = stage_groups(named_options)
    stages = {
        "schema": "hop.selected-scaffold-stages/v1",
        "endpoint": pool["endpoint"],
        "comparison_stage": pool["comparison_stage"],
        "stage_groups": groups,
        "options": named_options,
        "selected_options": list(members),
        "baseline": baseline,
        "scaffold": pool["scaffold"],
    }
    files["stage-comparison.json"] = canonical_json_bytes(stages)
    terminals = pool["endpoint"] == "adapter_ligated_hairpin" and any(
        d in pool["scaffold"] for d in ("five_prime_unpaired_nt", "three_prime_unpaired_nt")
    )
    if terminals or any(len(group["option_labels"]) > 1 for group in groups["endpoint"]):
        pages = terminal_plates(stages, files) if terminals else discovery_plates(stages, files)
        page_name = "terminal-forms" if terminals else "stage-comparison"
        files.update({f"pages/{page_name}-{i + 1}.svg": page for i, page in enumerate(pages)})
        files["report.pdf"] = render_report_pdf(tuple(pages))
    report = (
        f"Comparison stage: {pool['comparison_stage']}. "
        f"{len(groups['hairpin'])} distinct hairpins; "
        f"{len(groups['endpoint'])} distinct endpoint products.\n\n"
        "Set shared-property checks apply to hairpin architecture; "
        "stage-comparison.json records exact stage identities separately.\n\n"
        + selected.report_text
    )
    packet = ConstructionSet._create(files, summary, report)
    object.__setattr__(packet, "_roots", (protected,))
    return packet
