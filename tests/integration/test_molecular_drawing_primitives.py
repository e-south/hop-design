"""Editable scene primitives preserve molecular identity and literal input sequences."""

import json
from itertools import pairwise
from math import hypot
from xml.etree import ElementTree as ET

from hop_design import construction
from tests.integration.test_molecular_atlas import atlas_request

SVG = "{http://www.w3.org/2000/svg}"


def test_strand_groups_retain_every_base_and_explicit_direction(loop_pool):
    choices, request = atlas_request(loop_pool)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    root = ET.fromstring(packet.svg_bytes)
    atlas = json.loads(packet.json_bytes)["atlas"]
    for state in atlas["states"]:
        row = next(
            e for e in root.iter() if e.get("data-atlas-state") == state["state"]["state_id"]
        )
        groups = {
            e.get("data-strand-primitive"): e for e in row.iter() if e.get("data-strand-primitive")
        }
        assert set(groups) == {m["strand_id"] for m in state["state"]["molecules"]}
        for molecule in state["state"]["molecules"]:
            group = groups[molecule["strand_id"]]
            assert group.get("id") and group.get("data-sequence-direction") == "5prime-to-3prime"
            bases = [e for e in group.iter() if e.get("data-base-index") is not None]
            assert "".join(e.find(SVG + "text").text for e in bases) == molecule["sequence"]
            assert {e.find(SVG + "text").get("fill") for e in bases} == {"#182B34"}


def test_bound_primers_show_the_exact_ordered_sequence_without_becoming_state_bases(loop_pool):
    choices, request = atlas_request(loop_pool)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    root = ET.fromstring(packet.svg_bytes)
    inputs = json.loads(packet.json_bytes)["atlas"]["inputs"]
    for item in inputs:
        if item["binding_state_id"] != item["pre_state_id"]:
            continue
        primer = next(
            e for e in root.iter() if e.get("data-primer-binding") == item["material_use"]["use_id"]
        )
        bases = [e for e in primer.iter() if e.get("data-input-base-index") is not None]
        assert "".join(e.text for e in bases) == item["material"]["sequence_5prime"]
        assert not any(e.get("data-base-index") for e in primer.iter())
        assert primer.get("id")
        # A binding crossing a handle bend follows that recorded template,
        # rather than laying its letters along the chord between endpoints.
        row = next(e for e in root.iter() if e.get("data-atlas-state") == item["binding_state_id"])
        template = {
            int(e.get("data-base-index")): e
            for e in row.iter()
            if e.get("data-strand-id") == item["binding"]["template_strand_id"]
            and e.get("data-base-index") is not None
        }
        span = item["binding"]["template_span"]
        indices = list(reversed(range(span["start"]["offset"], span["end"]["offset"])))
        path = []
        for index in indices:
            rect = template[index].find(SVG + "rect")
            text = template[index].find(SVG + "text")
            path.append((float(rect.get("x")) + 7, float(text.get("y")) - 5))
        for glyph in bases[-len(indices) :]:
            x, y = float(glyph.get("x")) + 5, float(glyph.get("y")) - 5
            distances = []
            for (ax, ay), (bx, by) in pairwise(path):
                dx, dy = bx - ax, by - ay
                t = min(1, max(0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
                distances.append(hypot(x - ax - t * dx, y - ay - t * dy))
            # Normal clearance stays uniform through the kink. A miter may be
            # farther from the corner point, but never nearer than the clearance.
            assert min(distances) >= 44 - 1e-5


def test_cut_marks_are_strand_specific_and_site_bands_remain_translucent(loop_pool):
    choices, request = atlas_request(loop_pool)
    root = ET.fromstring(construction.inspect_scaffold_atlas(loop_pool, choices, request).svg_bytes)
    cuts = [e for e in root.iter() if e.get("data-cut")]
    assert cuts and all(e.get("id") and e.get("data-cut-point") for e in cuts)
    sites = [e for e in root.iter() if e.get("data-site-id")]
    assert sites and all(e.get("id") for e in sites)
    for site in sites:
        bands = [e for e in site.iter() if e.get("data-recognition-footprint")]
        if site.get("data-presence") in {"present", "partial"}:
            assert bands
        if site.get("data-presence") in {"not_yet_present", "removed"}:
            assert not bands
        assert all(e.tag == SVG + "path" and e.get("fill") != "none" for e in bands)
        assert all(0 < float(e.get("fill-opacity")) <= 0.2 for e in bands)
