"""Project a selected comparison from already verified member routes."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.export.construction.molecular.atlas import render_molecular_atlas
from hop_design.export.construction.molecular.teaching import render_parameter_teaching
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.comparisons.request import resolved_stage_controls
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.intents.comparison import InsertDesignSetSelection
from hop_design.serialization import canonical_json_bytes

from ...comparisons.controls import assess_stage_controls, stage_facts
from ...packets.atlas import MolecularAtlasPacket
from ...projections.atlas import project_molecular_atlas
from ...projections.atlas_comparison import compare_route_atlases
from ...projections.parameter_locations import parameter_locations
from ...projections.parameter_teaching import parameter_teaching, survey_teaching_axes


@dataclass(frozen=True, init=False, repr=False)
class InsertComparisonAtlas(MolecularAtlasPacket):
    _packet_schema: ClassVar[str] = "hop.insert-comparison-atlas-packet/v1"


def comparison_handoff(
    selected: InsertDesignSetSelection,
    routes: dict[str, MaterializedConstructionRealization],
    options: dict[str, dict[str, Any]],
    landscape: dict[str, Any],
    enzyme_names: dict[str, str],
    root: Path,
    source_root: Path,
) -> dict[str, Any]:
    """Keep retrieval's verified authority; rendering never reopens or searches it."""
    reference = routes[selected.baseline]
    reference_option = options[reference.materialized_realization_id]
    stage = selected.request.stage
    controls = assess_stage_controls(
        resolved_stage_controls(selected.request),
        {name: stage_facts(route) for name, route in routes.items()},
    )
    if any(control["status"] != "shared" for control in controls):
        raise ValueError("Retrieved routes do not satisfy the selected stage controls.")
    members = {}
    requirements = {member.name: member for member in selected.request.required_members}
    for name, route in routes.items():
        option = options[route.materialized_realization_id]
        comparison = compare_route_atlases(
            reference, route, reference=selected.baseline, option=name
        )
        atlas = project_molecular_atlas(route, enzyme_names=enzyme_names)
        locations = parameter_locations(route, atlas, option["values"])
        teaching = parameter_teaching(
            route,
            atlas,
            locations,
            option["values"],
            survey_teaching_axes(landscape["axes"]),
            landscape["context"],
        )
        packet = InsertComparisonAtlas._create(
            {
                "projection.svg": render_molecular_atlas(
                    atlas, comparison=comparison, parameter_locations=locations
                ),
                "teaching.svg": render_parameter_teaching(
                    teaching, atlas, locations, comparison=comparison
                ),
                "teaching.json": canonical_json_bytes(teaching),
            },
            {
                "atlas": atlas.model_dump(mode="json"),
                "comparison": comparison.model_dump(mode="json"),
            },
            f"# {name}\n\n[Measurements](teaching.svg) and [complete route](projection.svg).\n",
        )
        object.__setattr__(packet, "_roots", (ProtectedRoot.capture(source_root),))
        packet.write(root / "members" / name / "views", print_pages=False)
        members[name] = {
            "materialized_realization_id": route.materialized_realization_id,
            "loop_word": option["values"]["loop_word"],
            "required_dimensions": requirements[name].dimensions,
            "required_loop": requirements[name].loop_sequence,
            "required_release_method": enzyme_names.get(
                requirements[name].release_enzyme_id or "", requirements[name].release_enzyme_id
            ),
            "same_substrate": option["molecular_identity"][stage]
            == reference_option["molecular_identity"][stage],
            "changed_roles": list(comparison.material_roles),
            "comparison": comparison.model_dump(mode="json"),
        }
    return {
        "schema": "hop.selected-insert-comparison/v1",
        "stage": selected.request.stage,
        "baseline": selected.baseline,
        "stage_controls": controls,
        "shared_properties": list(selected.request.shared_properties),
        "preserve_material_roles": list(selected.request.preserve_material_roles),
        "groups": [group.model_dump(mode="json") for group in selected.request.groups],
        "members": members,
    }
