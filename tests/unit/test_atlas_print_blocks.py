"""Explicit chronology survives nonmonotone page coordinates."""

from xml.etree import ElementTree as ET

import pytest

from hop_design.export.construction.molecular.printing.atlas import paginate_atlas


def route():
    rows = "".join(
        f'<g data-atlas-state="s{i}" data-atlas-order="{i}" '
        f'data-atlas-x="{1200 if i > 1 else 32}" data-atlas-y="{32 + 500 * (i % 2)}" '
        'data-atlas-width="1000" data-atlas-height="450" data-atlas-anchor="200" '
        f'data-atlas-phase="{phase}">'
        f'<g data-base-index="0" data-occurrence="s{i}"><text font-size="16">A</text></g>'
        f'<text data-atlas-input="p{i}" font-size="16" font-family="monospace">ACGT</text></g>'
        for i, phase in enumerate(
            ["source_ssdna", "pcr_duplex", "hairpin_pcr_duplex", "clone_ready_duplex"]
        )
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2400 3000" '
        'data-atlas="true" data-atlas-layout="columns-with-finish"><g>' + rows + "</g></svg>"
    ).encode()


def test_pages_follow_explicit_order_and_preserve_all_occurrences_and_inputs():
    pages, layout = paginate_atlas(route())
    assert pages  # Empty declared canvas margins no longer force extra pages.
    roots = [ET.fromstring(p) for p in pages]
    assert [
        e.get("data-occurrence") for r in roots for e in r.iter() if e.get("data-occurrence")
    ] == [f"s{i}" for i in range(4)]
    assert [
        e.get("data-atlas-input") for r in roots for e in r.iter() if e.get("data-atlas-input")
    ] == [f"p{i}" for i in range(4)]
    assert [s for p in layout["pages"] for s in p["state_ids"]] == [f"s{i}" for i in range(4)]
    for root in roots:
        width = float(root.get("width").removesuffix("pt"))
        assert width / float(root.get("viewBox").split()[2]) * 16 >= 8 - 1e-8
    assert layout["minimum_annotation_font_pt"] == 9
    for root in roots:
        scale = float(root.get("width").removesuffix("pt")) / float(root.get("viewBox").split()[2])
        footer = root[-1]
        assert "Print at 100%" in footer.text
        assert float(footer.get("font-size")) * scale >= layout["minimum_annotation_font_pt"]
    assert paginate_atlas(route()) == (pages, layout)


def test_print_notes_use_the_page_type_budget_without_losing_comparison_context():
    root = ET.fromstring(route())
    notes = ET.SubElement(root[0], "{http://www.w3.org/2000/svg}g", {"data-atlas-notes": "true"})
    sentences = [
        f"Comparison {i}: the selected source and adapter differ "
        "while the supplied stem is preserved."
        for i in range(10)
    ]
    for sentence in sentences:
        ET.SubElement(
            notes, "{http://www.w3.org/2000/svg}text", {"font-size": "48"}
        ).text = sentence
    pages, _ = paginate_atlas(ET.tostring(root))
    printed = []
    for page in pages:
        document = ET.fromstring(page)
        assert float(document.get("height").removesuffix("pt")) <= 720
        scale = 504 / float(document.get("viewBox").split()[2])
        for group in document.iter():
            if group.get("data-atlas-notes"):
                for text in group.iter():
                    if text.tag.endswith("}text"):
                        assert float(text.get("font-size")) * scale == 12
                        printed.append(text.text)
    assert " ".join(" ".join(printed).split()) == " ".join(sentences)


def test_multipage_print_keeps_the_footprint_key_and_its_color_binding():
    root = ET.fromstring(route())
    key = ET.SubElement(
        root[0],
        "{http://www.w3.org/2000/svg}g",
        {
            "data-site-key": "true",
            "data-site-key-entries": '[["Nickase", "#146F54"]]',
        },
    )
    ET.SubElement(key, "{http://www.w3.org/2000/svg}text").text = "Nickase"
    pages, _ = paginate_atlas(ET.tostring(root))
    keys = [e for page in pages for e in ET.fromstring(page).iter() if e.get("data-site-key")]
    assert len(keys) == 1
    assert "Nickase" in "".join(keys[0].itertext())
    assert any(e.get("stroke") == "#146F54" for e in keys[0])
    assert "partial" in "".join(keys[0].itertext())


@pytest.mark.parametrize(
    "old,new",
    [
        (b'data-atlas-order="2"', b'data-atlas-order="0"'),
        (b'data-atlas-width="1000"', b'data-atlas-width="nan"'),
        (b'data-atlas-height="450"', b'data-atlas-height="-1"'),
        (b'data-atlas-state="s2"', b'data-atlas-state="s0"'),
    ],
)
def test_invalid_block_metadata_is_rejected(old, new):
    with pytest.raises(ValueError):
        paginate_atlas(route().replace(old, new))
