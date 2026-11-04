"""Produce a portable report without new search, relaxation or automatic selection."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.runtime import producer_identity
from hop_design.export.construction.scaffold.closing_svg import render_closing_svg
from hop_design.export.construction.scaffold.family_report import render_family_report
from hop_design.export.construction.scaffold.product_stages_svg import render_product_stages_svg
from hop_design.export.construction.scaffold.report_pdf import render_report_pdf, rendering_identity
from hop_design.models.construction.family.controls import ComparisonControl
from hop_design.models.construction.projections.family_report import (
    ConstructionFamilyReportProjection,
    FamilyReportChoice,
    FamilyReportMember,
)
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection
from hop_design.serialization import sha256_digest

from ..projections.product_stages import project_product_stages
from ..projections.trajectory import project_complete_construction_trajectory
from ..public import project_hairpin_portrait
from .admission import admit_family
from .capture import capture_family, write_snapshot
from .choices import describe_choice
from .comparisons import compare_family_members
from .controls import assess_controls
from .edits import describe_edits
from .member_admission import _equal
from .packet import SourceBoundFamilyPacket
from .properties import MOLECULAR_CONTROLS, shared_values
from .recovery import describe_recovery
from .selection import select_construction_set


@dataclass(frozen=True, init=False, repr=False)
class ConstructionFamilyReport(SourceBoundFamilyPacket):
    """Read-only comparison and exact preparations, bound to admitted family outcomes."""

    _packet_schema: ClassVar[str] = "hop.construction-family-report-packet/v1"


def project_construction_family_report(
    path: str | Path,
    *,
    selection: str | Path | None = None,
    baseline: str | None = None,
    edits: tuple[tuple[str, str], ...] = (),
) -> ConstructionFamilyReport:
    root, captured = capture_family(path)
    files = {f"family/{name}": content for name, content in captured.items()}
    roots = [root]
    selected = set()
    set_id = None
    selected_controls: tuple[ComparisonControl, ...] = ()
    selection_names = {}
    compared_properties: tuple[str, ...] = ()
    if selection is not None:
        packet = select_construction_set(selection)
        roots.extend(packet._roots)
        selected_summary = json.loads(packet.json_bytes)
        set_id = selected_summary["set_id"]
        compared_properties = tuple(selected_summary["compared_properties"])
        selected_controls = tuple(
            ComparisonControl.model_validate_json(json.dumps(c))
            for c in selected_summary["comparison_controls"]
        )
        selected = {
            (m["source_result_id"], m["materialized_realization_id"])
            for m in selected_summary["members"]
        }
        selection_names = {
            (m["source_result_id"], m["materialized_realization_id"]): m["name"]
            for m in selected_summary["members"]
        }
        files.update({f"selected/{name}": content for name, content in packet._files})
    members = []
    selected_names = []
    available = set()
    reference = None
    shared_reference = None
    display = []
    control_values: dict[str, dict[str, Any] | None] = {}
    control_reference = None
    with tempfile.TemporaryDirectory(prefix="hop-family-report-") as temporary:
        snapshot = Path(temporary) / "source"
        write_snapshot(captured, snapshot)
        recorded, admitted = admit_family(snapshot)
        comparisons = compare_family_members(admitted, baseline, selected)
        for member in admitted:
            choices = []
            recorded_choices = []
            if member.receipt is not None:
                for ordinal, identity in enumerate(member.receipt.materialized_realization_ids):
                    portrait = project_hairpin_portrait(
                        member.receipt, materialized_realization_id=identity
                    )
                    data = json.loads(portrait.json_bytes)
                    values = shared_values(data, recorded["shared_properties"])
                    control_name = (
                        member.name
                        if len(member.receipt.materialized_realization_ids) == 1
                        else f"{member.name}/{ordinal}"
                    )
                    control_values[control_name] = shared_values(data, MOLECULAR_CONTROLS)
                    if control_reference is None:
                        control_reference = control_name
                    if reference is None:
                        reference = values
                        shared_reference = {"member": member.name, "properties": reference}
                    described = describe_choice(
                        member.name, ordinal, data, recorded["shared_properties"], reference
                    )
                    recorded_choices.append(described)
                    differences = described["shared_property_differences"]
                    if not differences:
                        preference = tuple(
                            (1 if p["direction"] == "ascending" else -1) * values[p["dimension"]]
                            for p in recorded["display_preferences"]
                        )
                        display.append((preference, member.name, identity))
                    exact = (member.receipt.result_id, identity)
                    available.add(exact)
                    is_selected = exact in selected
                    if is_selected and differences:
                        raise ValueError("Selected member contradicts family shared requirements.")
                    if is_selected and member.name not in selected_names:
                        selected_names.append(member.name)
                    prefix = f"members/{member.name}/choices/{ordinal}"
                    directory = portrait.write(Path(temporary) / member.name / str(ordinal))
                    for artifact in directory.rglob("*"):
                        if artifact.is_file():
                            files[f"{prefix}/{artifact.relative_to(directory).as_posix()}"] = (
                                artifact.read_bytes()
                            )
                    svg_path = f"{prefix}/projection.svg"
                    trajectory = project_complete_construction_trajectory(
                        member.receipt._verified_source(), materialized_realization_id=identity
                    )
                    portrait_facts = HairpinPortraitProjection.model_validate_json(
                        portrait.json_bytes
                    )
                    stages = project_product_stages(portrait_facts, trajectory)
                    closing_path = f"{prefix}/closing-region.svg"
                    files[closing_path] = render_closing_svg(portrait_facts)
                    stage_path = f"{prefix}/product-stages.svg"
                    files[stage_path] = render_product_stages_svg(stages, files[svg_path])
                    choices.append(
                        FamilyReportChoice(
                            source_result_id=exact[0],
                            materialized_realization_id=identity,
                            geometry={
                                key: data[key]
                                for key in (
                                    "loop_nt",
                                    "loop_side_paired_bp",
                                    "open_side_paired_positions",
                                    "stem_bp",
                                )
                            },
                            portrait=svg_path,
                            preparation=f"{prefix}/preparation/report.md",
                            selected=is_selected,
                            selection_name=selection_names.get(exact),
                            stage=data["state"]["phase"],
                            stage_role=data["stage_role"],
                            endpoint=data["endpoint"],
                            shared_property_differences=tuple(differences),
                            product_stages=stages,
                            stage_drawing=stage_path,
                            closing_drawing=closing_path,
                        )
                    )
            outcome = member.outcome
            if not choices:
                control_values[member.name] = None
            original = next(row for row in recorded["members"] if row["name"] == member.name)
            _equal(original["choices"], recorded_choices, f"{member.name} choices")
            members.append(
                FamilyReportMember(
                    name=member.name,
                    requested_variation=member.preview["requested_variation"],
                    effective_geometry=member.preview["effective_geometry"],
                    status=outcome["status"],
                    stage=outcome["stage"],
                    scope=outcome["scope"],
                    local_coverage=outcome["local_coverage"],
                    rejection_reasons=tuple(outcome["rejection_reasons"]),
                    preparation_constraints=tuple(outcome.get("preparation_constraints", [])),
                    choices=tuple(choices),
                )
            )
    display_choices = [
        {"member": name, "materialized_realization_id": identity}
        for _, name, identity in sorted(display)
    ]
    _equal(recorded["shared_reference"], shared_reference, "shared reference")
    _equal(recorded["display_choices"], display_choices, "display choices")
    _equal(
        recorded["display_order"],
        list(dict.fromkeys(c["member"] for c in display_choices)),
        "display order",
    )
    if selected - available:
        raise ValueError("Selected constructions do not belong to the verified family outcomes.")
    if baseline is not None and baseline not in {m.name for m in members if m.choices}:
        raise ValueError("Comparison baseline must name a complete family member.")
    projection = ConstructionFamilyReportProjection(
        family_id=recorded["family_id"],
        source_manifest_digest=sha256_digest(captured["manifest.json"]),
        recorded_producer=recorded["producer"],
        report_producer={**producer_identity(), "rendering": rendering_identity()},
        shared_properties=tuple(recorded["shared_properties"]),
        upper_bounds=recorded["upper_bounds"],
        members=tuple(members),
        selected_members=tuple(selected_names),
        selection_set_id=set_id,
        baseline=baseline,
        interpretation=recorded["interpretation"],
        comparisons=comparisons,
        authored_edits=describe_edits(tuple(members), edits),
        revision=recorded.get("revision"),
        family_controls=assess_controls(
            control_values, control_reference, recorded["shared_properties"]
        ),
        selected_controls=selected_controls,
        recovery=describe_recovery(recorded.get("revision"), admitted),
        compared_properties=compared_properties,
    )
    report_text, pages = render_family_report(projection, files)
    files["report.svg"] = pages[0]
    files.update({f"pages/{i + 1}.svg": page for i, page in enumerate(pages)})
    files["report.pdf"] = render_report_pdf(pages)
    report_packet = ConstructionFamilyReport._create(
        files, projection.model_dump(mode="json", by_alias=True), report_text
    )
    object.__setattr__(report_packet, "_roots", tuple(roots))
    return report_packet
