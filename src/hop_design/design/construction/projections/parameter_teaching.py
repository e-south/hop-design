"""A preparation-bound teaching index; clients do not derive molecular meanings."""

from typing import Any

from hop_design.models.construction.complete.pcr.authority import AdapterAnnealingAuthority
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.projections.atlas import MolecularScenes
from hop_design.models.construction.projections.route_view import MolecularRouteView
from hop_design.models.construction.variants.parameters import parameter_definition


def survey_teaching_axes(axes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Adapt surveyed domains to the shared selected-measurement contract."""
    return [
        {
            "key": axis["key"],
            "values": axis["nodes"],
            "declared": axis["domain"],
            "fixed_by_request": len(axis["domain"].get("values", ())) == 1,
            "observed_variation": False,
        }
        for axis in axes
    ]


def parameter_teaching(
    route: MolecularRouteView,
    atlas: MolecularScenes,
    locations: list[dict[str, Any]],
    values: dict[str, Any],
    axes: list[dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Index exact coordinates and recorded facts, including nonspatial requirements."""
    located = {p["key"]: p for p in locations}
    parameters = []
    for axis in axes:
        key = axis["key"]
        definition = parameter_definition(key)
        value = values.get(key)
        location = located.get(key)
        if definition.representation == "context":
            coverage = "context"
        elif value is None:
            coverage = "not_applicable"
        elif location and location["reference_addresses"]:
            coverage = "located"
        elif location and location["boundary_anchors"]:
            coverage = "boundary"
        elif location and definition.representation == "contact" and value == 0:
            coverage = "empty_contact_set"
        else:
            raise ValueError(f"Teaching parameter {key} has no recorded molecular location.")
        label = next((v["label"] for v in axis["values"] if v["value"] == value), str(value))
        parameters.append(
            {
                "key": key,
                "value": value,
                "value_label": label if value is not None else "Not applicable",
                "definition": definition.model_dump(mode="json"),
                "coverage": coverage,
                "location_key": key if location else None,
                "effective_requirement_differs": (
                    definition.representation == "threshold"
                    and bool(axis["declared"].get("values"))
                    and value not in axis["declared"]["values"]
                ),
                "fixed_by_request": axis["fixed_by_request"],
                "observed_variation": axis["observed_variation"],
                "domain": axis["declared"],
            }
        )
    frames = [
        {
            "key": key,
            "title": title,
            "parameter_keys": [
                p["key"] for p in parameters if p["definition"]["glyph_frame"] in members
            ],
        }
        for key, title, members in (
            ("source_association", "Source and association", ("source", "association")),
            ("hairpin", "Folded hairpin", ("hairpin",)),
            ("insert", "Released insert", ("insert",)),
        )
    ]
    contacts = []
    for p in parameters:
        if not p["key"].startswith("basal_source_base_") or p["value"] is None:
            continue
        i = p["definition"]["position_from_ligation"]
        keys = [f"basal_{kind}_{i}" for kind in ("source_base", "adapter_base", "pair_class")]
        contacts.append(
            {
                "position_from_ligation": i,
                "source_base": values[keys[0]],
                "adapter_base": values[keys[1]],
                "contact_class": values[keys[2]],
                "parameter_keys": keys,
            }
        )
    anatomy = describe_hairpin(route)
    association = []
    for transition in route.construction_program.transitions:
        authority = transition.pcr_authority
        if not isinstance(authority, AdapterAnnealingAuthority):
            continue
        state = next(s.state for s in atlas.states if s.state.state_id == authority.post_state_id)
        strands = {m.strand_id: m.sequence for m in state.molecules}
        for pair in sorted(authority.pairings, key=lambda p: p.right_index):
            i = pair.right_index - authority.adapter_span.start.offset
            association.append(
                {
                    "position_from_ligation": i,
                    "source_index": pair.left_index,
                    "adapter_index": pair.right_index,
                    "source_base": strands[pair.left_strand_id][pair.left_index],
                    "adapter_base": strands[pair.right_strand_id][pair.right_index],
                    "contact_class": pair.kind.value,
                    "parameter_keys": next(
                        (c["parameter_keys"] for c in contacts if c["position_from_ligation"] == i),
                        ["adapter_annealing_achieved_nt"],
                    ),
                }
            )
    source = route.source_preparation
    # Scene facts are shared by static and interactive glyphs. All addresses still
    # point to the exact atlas; proportional schematic placement adds no chemistry.
    source_state = next(
        s for s in atlas.states if s.state.state_id == source.product_state.state_id
    )
    operations = [
        o.model_dump(mode="json")
        for s in atlas.states
        for o in s.operations
        if o.timing == "planned"
    ]
    # Coordinate frames describe where a quantity is measured; they are not a
    # second processing route. Teach structure on the selected hairpin, adding
    # the released product only for its distinct end coordinates.
    scenes = [
        {"frame": "hairpin", "title": "Hairpin structure", "state_id": anatomy.state.state_id}
    ]
    if route.final_product.cohesive_ends:
        scenes.append(
            {
                "frame": "insert",
                "title": "Released insert",
                "state_id": atlas.states[-1].state.state_id,
            }
        )
    return {
        "schema": "hop.parameter-teaching/v1",
        "materialized_realization_id": atlas.materialized_realization_id,
        "frames": frames,
        "scenes": scenes,
        "parameters": parameters,
        "contacts": sorted(contacts, key=lambda p: p["position_from_ligation"]),
        "association_contacts": association,
        "source": {
            "state_id": source_state.state.state_id,
            "strands": [
                {"strand_id": m.strand_id, "sequence": m.sequence}
                for m in source_state.state.molecules
            ],
            "stem_span": source.payload_source_span.model_dump(mode="json"),
            "operations": [
                o for o in operations if o["precursor_state_id"] == source_state.state.state_id
            ],
            "recognition_sites": [
                s.model_dump(mode="json") for s in source_state.recognition_sites
            ],
        },
        "hairpin": anatomy.model_dump(mode="json", exclude={"state"}),
        "interfaces": [i.model_dump(mode="json") for s in atlas.states for i in s.interfaces],
        "release_operations": [o for o in operations if o["role"] == "end_generation"],
        "context": {
            "parameter_keys": [p["key"] for p in parameters if p["coverage"] == "context"],
            **context,
        },
    }
