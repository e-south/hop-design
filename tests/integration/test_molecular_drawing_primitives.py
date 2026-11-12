"""Editable scene primitives preserve molecular identity and literal input sequences."""

import json
from itertools import pairwise
from math import hypot
from xml.etree import ElementTree as ET

from hop_design import construction
from hop_design.export.construction.molecular.primitives.style import PRIMER_CLEARANCE, base_ink
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
            for base in bases:
                assert base.find(SVG + "text").get("fill") == base_ink(
                    base.get("data-neighborhood"), base.find(SVG + "rect").get("fill")
                )


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
            x, y = float(glyph.get("x")), float(glyph.get("y")) - 5
            distances = []
            for (ax, ay), (bx, by) in pairwise(path):
                dx, dy = bx - ax, by - ay
                t = min(1, max(0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
                distances.append(hypot(x - ax - t * dx, y - ay - t * dy))
            # Normal clearance stays uniform through the kink. A miter may be
            # farther from the corner point, but never nearer than the clearance.
            assert min(distances) >= PRIMER_CLEARANCE - 1e-5


def test_cut_marks_are_strand_specific_and_site_bands_remain_translucent(loop_pool):
    choices, request = atlas_request(loop_pool)
    root = ET.fromstring(construction.inspect_scaffold_atlas(loop_pool, choices, request).svg_bytes)
    cuts = [e for e in root.iter() if e.get("data-cut")]
    assert cuts and all(e.get("id") and e.get("data-cut-point") for e in cuts)
    sites = [e for e in root.iter() if e.get("data-site-id")]
    assert sites and all(e.get("id") for e in sites)
    for site in sites:
        bands = [e for e in site.iter() if e.get("data-recognition-footprint")]
        if site.get("data-footprint-display") == "metadata":
            assert not bands
            assert json.loads(site.get("data-recognition-addresses"))
        elif site.get("data-presence") in {"present", "partial"}:
            assert bands
        if site.get("data-presence") in {"not_yet_present", "removed"}:
            assert not bands
        assert all(e.tag == SVG + "path" and e.get("fill") != "none" for e in bands)
        assert all(0 < float(e.get("fill-opacity")) <= 0.2 for e in bands)


def test_watson_crick_links_stay_registered_to_their_recorded_base_centers(loop_pool):
    import re

    import pytest

    from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview

    choices, request = atlas_request(loop_pool)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    summary = json.loads(packet.json_bytes)
    route = ET.fromstring(packet.svg_bytes)
    views = [e for e in route.iter() if e.get("data-atlas-state")]
    views.append(ET.fromstring(render_teaching_overview(summary)))
    for view in views:
        centers = {}
        for base in (e for e in view.iter() if e.get("data-base-index") is not None):
            rect = base.find(SVG + "rect")
            text = base.find(SVG + "text")
            centers[base.get("data-strand-id"), int(base.get("data-base-index"))] = (
                float(rect.get("x")) + float(rect.get("width")) / 2,
                float(text.get("y")) - 5,
            )
        for link in (e for e in view.iter() if e.get("data-pair-kind") == "watson_crick"):
            a = centers[tuple(json.loads(link.get("data-from")))[-2:]]
            b = centers[tuple(json.loads(link.get("data-to")))[-2:]]
            x, y, u, v = map(float, re.findall(r"[-\d.]+", link.get("d")))
            length = hypot(b[0] - a[0], b[1] - a[1])
            # The contact remains on the line between its own two base centers,
            # with the existing ten-unit inset at each nucleotide tile.
            assert (x - a[0]) * (b[1] - a[1]) - (y - a[1]) * (b[0] - a[0]) == pytest.approx(
                0, abs=1e-6
            )
            assert (u - b[0]) * (b[1] - a[1]) - (v - b[1]) * (b[0] - a[0]) == pytest.approx(
                0, abs=1e-6
            )
            assert hypot(x - a[0], y - a[1]) == pytest.approx(min(10, length / 2))
            assert hypot(u - b[0], v - b[1]) == pytest.approx(min(10, length / 2))
