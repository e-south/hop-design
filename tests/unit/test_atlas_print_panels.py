"""Physical-width pages preserve every addressed base at a marked continuation."""

from xml.etree import ElementTree as ET

from hop_design.export.construction.molecular.printing.atlas import paginate_atlas


def wide_route():
    bases = "".join(
        f'<g data-base-index="{i}" data-occurrence="b{i}" data-strand-id="strand" '
        f'data-state-id="source"><rect x="{28 + i * 18}" y="90" width="14" height="20"/>'
        f'<text x="{30 + i * 18}" y="105" font-size="16">A</text></g>'
        for i in range(120)
    )
    edges = "".join(
        '<path data-edge-kind="backbone" '
        f'data-from="[&quot;source&quot;,&quot;strand&quot;,{i}]" '
        f'data-to="[&quot;source&quot;,&quot;strand&quot;,{i + 1}]" '
        f'd="M{42 + i * 18},100 L{46 + i * 18},100"/>'
        for i in range(119)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2400 500" '
        'data-atlas="true" data-atlas-layout="columns-with-finish"><g>'
        '<g data-atlas-state="source" data-atlas-order="0" data-atlas-width="2400" '
        'data-atlas-height="400" data-atlas-anchor="300" data-atlas-phase="source_ssdna">'
        '<text x="1200" y="30" font-size="28" data-stage-title="true">1. Source ssDNA</text>'
        + edges
        + bases
        + "</g></g></svg>"
    ).encode()


def test_wide_scene_uses_coordinate_continuations_at_seven_inches():
    pages, layout = paginate_atlas(wide_route())
    roots = [ET.fromstring(p) for p in pages]
    assert all(float(p.get("width").removesuffix("pt")) == 504 for p in roots)
    assert all(float(p.get("height").removesuffix("pt")) <= 720 for p in roots)
    assert len([e for p in roots for e in p.iter() if e.get("data-scene-panel")]) >= 3
    occurrences = [
        e.get("data-occurrence") for p in roots for e in p.iter() if e.get("data-occurrence")
    ]
    assert occurrences == [f"b{i}" for i in range(120)]
    intervals = [
        r for page in layout["pages"] for panel in page["panels"] for r in panel["base_spans"]
    ]
    assert sum(r["stop"] - r["start"] for r in intervals) == 120
    assert all(
        "Continue" in "".join(p.itertext()) or "continued" in "".join(p.itertext()) for p in roots
    )
    for page in roots:
        scale = 504 / float(page.get("viewBox").split()[2])
        for e in page.iter():
            if e.get("data-stage-title"):
                assert float(e.get("font-size")) * scale == 16
            if e.get("data-occurrence"):
                text = next(t for t in e if t.tag.endswith("}text"))
                assert float(text.get("font-size")) * scale >= 8
    assert paginate_atlas(wide_route()) == (pages, layout)


def test_continued_editable_groups_have_unique_svg_ids_on_each_page():
    svg = wide_route().replace(
        b"<path data-edge-kind=", b'<g id="strand-edit"><path data-edge-kind=', 1
    )
    svg = svg.replace(b"</g></g></svg>", b"</g></g></g></svg>")
    pages, _ = paginate_atlas(svg)
    for page in pages:
        ids = [e.get("id") for e in ET.fromstring(page).iter() if e.get("id")]
        assert len(ids) == len(set(ids))


def test_pdf_encoder_resolves_every_continuation_clip(caplog):
    from hop_design.export.construction.scaffold.report_pdf import render_report_pdf

    pages, _ = paginate_atlas(wide_route())
    assert all(b'xmlns="http://www.w3.org/2000/svg"' in p for p in pages)
    pdf = render_report_pdf(pages)
    assert pdf.startswith(b"%PDF")
    assert "Unable to find a clipping path" not in caplog.text


def test_page_height_includes_headers_and_spacing_at_the_physical_limit():
    tall = wide_route().replace(b'y="90"', b'y="1208"').replace(b'y="105"', b'y="1223"')
    pages, _ = paginate_atlas(tall)
    assert all(float(ET.fromstring(page).get("height").removesuffix("pt")) <= 720 for page in pages)


def test_print_preserves_primer_label_groups_when_splitting_the_route():
    import json

    from hop_design.export.construction.molecular.label_layout import LabelPlacer

    root = ET.fromstring(wide_route())
    row = next(e for e in root.iter() if e.get("data-atlas-state"))
    row.append(
        ET.fromstring(
            LabelPlacer().block(
                100,
                190,
                [
                    ("primer-binding", "Reverse", "#123", 48),
                    ("primer-chemistry", "P / OH", "#123", 32),
                ],
            )
        )
    )
    pages, _ = paginate_atlas(ET.tostring(root))
    groups = [g for p in pages for g in ET.fromstring(p).iter() if g.get("data-annotation-block")]
    assert len(groups) == 1
    boxes = [json.loads(e.get("data-label-box")) for e in groups[0] if e.get("data-label-box")]
    assert len(boxes) == 2
    assert boxes[0][0] == boxes[1][0]
    assert boxes[1][1] - boxes[0][1] - boxes[0][3] == 8
