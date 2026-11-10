"""One selected hairpin for the landscape; detailed measurements stay in the atlas.

Coordinates here only place recorded bases. Parameter occurrences and recognition
footprints come from the shared projection, including ancestry-qualified release
coordinates.
"""

import json
from typing import Any
from xml.etree import ElementTree as ET

from hop_design.export.construction.presentation.figure_profile import (
    PUBLICATION_FIGURE,
    FigureProfile,
)
from hop_design.export.construction.presentation.parameter_labels import parameter_labels
from hop_design.models.construction.projections.atlas import MolecularAtlas, MolecularScenes

from .assembly.inputs import incoming_materials
from .inspection_layout import inspection_points
from .inspection_scene import edge, region_spans
from .material_bindings import material_binding_overlays
from .parameter_boundaries import boundary_point
from .primitives.extent import scene_bounds
from .primitives.materials import input_box, staged_materials
from .primitives.style import FONT_FAMILY, INK, base_ink
from .primitives.typography import fitted_base_size, text_width
from .recognition_sites import recognition_site_overlays
from .teaching_annotations import (
    OverviewLabels,
    label_backplates,
    local_dimensions,
    projected_end_spans,
)

SVG = "http://www.w3.org/2000/svg"
WIDTH, HEIGHT = 1008, 230


def element(parent: ET.Element, tag: str, **attrs: Any) -> ET.Element:
    return ET.SubElement(
        parent, f"{{{SVG}}}{tag}", {k.replace("_", "-"): str(v) for k, v in attrs.items()}
    )


def text(parent: ET.Element, x: float, y: float, value: str, **attrs: Any) -> ET.Element:
    node = element(parent, "text", x=x, y=y, **attrs)
    node.text = value
    return node


def render_teaching_overview(
    summary: dict[str, Any], *, profile: FigureProfile = PUBLICATION_FIGURE
) -> bytes:
    """Admit a serialized atlas before rendering its exact teaching molecule."""
    atlas = MolecularAtlas.model_validate_json(json.dumps(summary["atlas"]))
    return render_projected_teaching(
        atlas, summary["teaching"], summary["parameter_locations"], profile=profile
    )


def render_projected_teaching(
    atlas: MolecularScenes,
    teaching: dict[str, Any],
    locations: list[dict[str, Any]],
    *,
    profile: FigureProfile = PUBLICATION_FIGURE,
) -> bytes:
    """Draw an already typed projection without serializing its complete route."""
    return _render_projected_teaching(atlas, teaching, locations, profile=profile)


def _render_projected_teaching(
    atlas: MolecularScenes,
    teaching: dict[str, Any],
    locations: list[dict[str, Any]],
    *,
    profile: FigureProfile,
    annotation_shift: float = 0,
) -> bytes:
    definitions, label_projection = parameter_labels(
        [location["definition"] for location in locations]
    )
    displayed_definitions = {definition["key"]: definition for definition in definitions}
    if teaching["materialized_realization_id"] != atlas.materialized_realization_id:
        raise ValueError("Teaching overview and atlas must describe the same preparation.")
    scene = next(s for s in teaching["scenes"] if s["frame"] == "hairpin")
    state = next(s for s in atlas.states if s.state.state_id == scene["state_id"])
    raw = inspection_points(state)
    low, high = min(x for x, _ in raw.values()), max(x for x, _ in raw.values())
    # Fit a single structure, never repeat it as continuation rows. Keep the
    # sequence pitch where it fits; the detailed export owns long-sequence print.
    # Baseline belongs to the molecular coordinate frame, not to a mutable
    # publication style. Changing print type must not move the inspector frame.
    label_delta = profile.teaching_font - 18
    shift = 4 * label_delta + annotation_shift
    loop_room = 20 if profile.loop_label_below else text_width("12 nt", profile.teaching_font) + 30
    left = 40 if profile.loop_label_below else 80
    scale = min(1.0, (WIDTH - left - 20 - loop_room) / max(1, high - low))
    top, bottom = min(y for _, y in raw.values()), max(y for _, y in raw.values())
    points = {
        k: (left + (x - low) * scale, y - (top + bottom) / 2 + 180 + shift)
        for k, (x, y) in raw.items()
    }
    labels = OverviewLabels(points, width=WIDTH, size=profile.teaching_font)
    annotation = labels.text
    # Reserve actual uppercase glyph width within the horizontal nucleotide pitch.
    # Large annotation type must not compress neighboring letters into each other.
    widest_base = max(text_width(base, 1) for base in "ACGT")
    horizontal_steps = [
        abs(x - following[0])
        for (strand, index), (x, y) in points.items()
        if (following := points.get((strand, index + 1))) is not None
        and following[1] == y
        and following[0] != x
    ]
    pitch = min(horizontal_steps, default=float(profile.teaching_base_font))
    font = min(float(profile.teaching_base_font), max(0.1, pitch - 0.5) / widest_base)
    root = ET.Element(
        f"{{{SVG}}}svg",
        {
            "viewBox": f"0 0 {WIDTH} {HEIGHT}",
            "width": "7in",
            "height": f"{7 * HEIGHT / WIDTH}in",
            "role": "img",
            "aria-label": "Selected hairpin and its parameter locations",
            "font-family": FONT_FAMILY,
            "font-size": str(profile.teaching_font),
            "fill": INK,
            "data-preparation-id": atlas.materialized_realization_id,
            "data-teaching-resolution": "every-base",
            "data-teaching-composition": "single-hairpin",
        },
    )
    element(root, "rect", width=WIDTH, height=HEIGHT, fill="white")
    element(root, "metadata", data_parameter_labels="true").text = json.dumps(label_projection)
    group = element(root, "g", data_teaching_frame="hairpin", data_state_id=scene["state_id"])
    keys_by_base: dict[tuple[str, int], list[str]] = {}
    for location in locations:
        for address in location["occurrences"]:
            if address["state_id"] == scene["state_id"]:
                keys_by_base.setdefault((address["strand_id"], address["index"]), []).append(
                    location["key"]
                )
    # Shared contours, palette and footprint geometry; composition stays local.
    shared = ET.fromstring(f'<g xmlns="{SVG}">' + region_spans(state, points) + "</g>")
    group.extend(list(shared))
    for pair in state.state.pairings:
        group.append(
            ET.fromstring(
                edge(
                    "pair",
                    (pair.left_strand_id, pair.left_index),
                    (pair.right_strand_id, pair.right_index),
                    points,
                    pair_kind=pair.kind.value,
                )
            )
        )
    for base in state.bases:
        x, y = points[base.address.strand_id, base.address.index]
        glyph = element(
            group,
            "g",
            data_base_index=base.address.index,
            data_base=base.base,
            data_state_id=scene["state_id"],
            data_strand_id=base.address.strand_id,
            data_neighborhood=base.neighborhood or "",
            data_region=base.region or "",
            data_preparation_id=atlas.materialized_realization_id,
            data_teaching_keys=json.dumps(
                keys_by_base.get((base.address.strand_id, base.address.index), [])
            ),
        )
        element(
            glyph,
            "rect",
            x=x - 7,
            y=y - 10,
            width=14,
            height=20,
            rx=3,
            fill="none",
        )
        text(
            glyph,
            x,
            y + 5,
            base.base,
            text_anchor="middle",
            font_family=FONT_FAMILY,
            font_size=fitted_base_size(base.base, font, pitch=pitch),
            fill=base_ink(base.neighborhood or "unmapped"),
        )
        element(
            glyph, "title"
        ).text = f"{base.base} · {base.region} · position {base.address.index + 1}"
    # Each connector originates at a recorded feature on this one hairpin.
    # Release words/gaps are projected by ancestry, not drawn as exposed ends.
    for location in locations:
        addresses = [a for a in location["occurrences"] if a["state_id"] == scene["state_id"]]
        located = [
            points[a["strand_id"], a["index"]]
            for a in addresses
            if (a["strand_id"], a["index"]) in points
        ]
        zero = not located and location.get("zero_extent", False)
        if zero:
            qualified = {
                (scene["state_id"], strand, index): point
                for (strand, index), point in points.items()
            }
            located = [
                point
                for anchor in location.get("boundary_occurrences", location["boundary_anchors"])
                if anchor["start"] == anchor["end"]
                for point in (boundary_point(anchor["start"], qualified),)
                if point is not None
            ]
        if not located:
            continue
        x0, x1 = min(p[0] for p in located) - 7, max(p[0] for p in located) + 7
        y0, y1 = min(p[1] for p in located) - 11, max(p[1] for p in located) + 11
        key = location["key"]
        definition = displayed_definitions[key]
        anchor = element(
            group,
            "g",
            data_parameter_anchor=key,
            data_parameter_label=definition["label"],
            data_teaching_keys=json.dumps([key]),
            data_anchor_box=json.dumps([x0, y0, x1 - x0, y1 - y0]),
        )
        element(anchor, "title").text = f"{definition['label']}: {definition['measurement']}"
        if zero:
            anchor.set("data-zero-extent", "true")
            for x, y in located:
                element(
                    anchor,
                    "path",
                    d=f"M {x - 4} {y + 15} h 8 M {x} {y + 11} v 8",
                    fill="none",
                    stroke=INK,
                    stroke_width=1.5,
                )
        if key == "noncanonical_pairs":
            member_keys = {(a["strand_id"], a["index"]) for a in addresses}
            contacts = []
            for pair in state.state.pairings:
                left_key = (pair.left_strand_id, pair.left_index)
                right_key = (pair.right_strand_id, pair.right_index)
                if pair.kind.value != "watson_crick" and {left_key, right_key} <= member_keys:
                    a, b = points[left_key], points[right_key]
                    contacts.append([(a[0] + b[0]) / 2 - 5, (a[1] + b[1]) / 2 - 6, 10, 12])
            if contacts:
                anchor.set("data-anchor-regions", json.dumps(contacts))
    # Reserve complete incoming and bound primer contours before locating any
    # neighborhood labels. Their wedges extend beyond nucleotide centers.
    staged = incoming_materials(atlas, state, {state.state.state_id: points})
    labels.placer.occupied.extend(
        input_box(i.positions, primer=i.item.binding is not None, outward=i.outward) for i in staged
    )
    bindings = tuple(
        i
        for i in atlas.inputs
        if i.pre_state_id == state.state.state_id and i.binding_state_id == state.state.state_id
    )
    overlays = material_binding_overlays(
        bindings, points, labels.placer, base_size=font
    ) + staged_materials(staged, labels.placer, base_size=font)
    regions = (("assembly", "Basal"), ("stem", "Supplied stem"), ("closing", "Foldback"))
    for neighborhood, name in regions:
        xs = [
            points[b.address.strand_id, b.address.index][0]
            for b in state.bases
            if b.neighborhood == neighborhood
        ]
        if xs:
            annotation(
                group,
                (min(xs) + max(xs)) / 2,
                20 + label_delta,
                name,
                text_anchor="middle",
                font_weight=600,
            )
    for strand in state.state.molecules:
        for i, label, dy in ((0, "5\u2032", -18), (len(strand.sequence) - 1, "3\u2032", 18)):
            x, y = points[strand.strand_id, i]
            annotation(group, x - 8, y + dy, label, text_anchor="end", font_size=18)
    values = {p["key"]: p["value_label"] for p in teaching["parameters"] if p["value"] is not None}
    loop_points = [
        points[b.address.strand_id, b.address.index]
        for b in state.bases
        if b.neighborhood == "loop"
    ]
    if loop_points:
        annotation(
            root,
            max(x for x, _ in loop_points) + (-10 if profile.loop_label_below else 25),
            max(y for _, y in loop_points) + 50
            if profile.loop_label_below
            else sum(y for _, y in loop_points) / len(loop_points) + profile.teaching_font / 3,
            f"{values.get('loop_nt', '')} nt",
            text_anchor="end" if profile.loop_label_below else "start",
            data_teaching_note="loop",
            data_teaching_keys=json.dumps(["loop_nt", "loop_word"]),
        )
    overlays += recognition_site_overlays(
        state, points, labels.placer, label_size=profile.teaching_font, strand_labels=True
    )
    root.extend(list(ET.fromstring(f'<g xmlns="{SVG}">' + overlays + "</g>")))
    local_dimensions(root, scene["state_id"], points, teaching, locations, labels)
    projected_end_spans(root, labels)
    element(root, "metadata", data_teaching_parameters="true").text = json.dumps(
        teaching["parameters"], sort_keys=bool(label_delta)
    )
    label_top = min(
        (json.loads(e.attrib["data-label-box"])[1] for e in root.iter() if e.get("data-label-box")),
        default=4,
    )
    if label_top < 4 - 1e-7:
        return _render_projected_teaching(
            atlas,
            teaching,
            locations,
            profile=profile,
            annotation_shift=annotation_shift + 4 - label_top,
        )
    height = max(HEIGHT, labels.bottom + 10)
    label_backplates(root)
    x, y, width, content_height = scene_bounds(root)
    root.set("data-content-frame", f"{x - 8:g} {y - 8:g} {width + 16:g} {content_height + 16:g}")
    root.set("viewBox", f"0 0 {WIDTH} {height}")
    root.set("height", f"{7 * height / WIDTH}in")
    next(e for e in root if e.tag.endswith("}rect")).set("height", str(height))
    return bytes(ET.tostring(root, encoding="utf-8"))
