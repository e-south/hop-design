"""Print pagination preserves the exact route instead of shrinking nucleotide text."""

from xml.etree import ElementTree as ET

import pytest

from hop_design.export.construction.molecular.printing.atlas import paginate_atlas


def route():
    rows = "".join(
        f'<g data-atlas-state="s{i}" data-atlas-y="{50 + 600 * i}" '
        f'transform="translate(0 {50 + 600 * i})">'
        f'<text font-size="16" data-base-index="0" data-occurrence="s{i}">A</text>'
        "</g>"
        f'<text data-input="p{i}" x="58" y="{550 + 600 * i}" '
        'font-size="14" font-family="monospace">ACGT</text>'
        for i in range(4)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2200 2450" '
        'data-atlas="true"><rect width="100%" height="100%" fill="white"/>'
        '<g font-family="Arial, Helvetica, sans-serif">'
        '<text x="28" y="30" font-size="24">Complete molecular preparation</text>'
        f"{rows}</g></svg>"
    ).encode()


def test_pages_keep_every_state_base_and_input_once_at_readable_physical_size():
    pages, layout = paginate_atlas(route())
    assert len(pages) == 2
    roots = [ET.fromstring(page) for page in pages]
    assert [
        e.get("data-atlas-state") for p in roots for e in p.iter() if e.get("data-atlas-state")
    ] == ["s0", "s1", "s2", "s3"]
    assert [
        e.get("data-occurrence") for p in roots for e in p.iter() if e.get("data-occurrence")
    ] == ["s0", "s1", "s2", "s3"]
    assert [e.get("data-input") for p in roots for e in p.iter() if e.get("data-input")] == [
        "p0",
        "p1",
        "p2",
        "p3",
    ]
    for page in roots:
        width = float(page.get("width").removesuffix("pt"))
        scale = width / float(page.get("viewBox").split()[2])
        for e in page.iter():
            if e.get("data-base-index") is not None or e.get("font-family") == "monospace":
                assert float(e.get("font-size")) * scale >= 8 - 1e-8
    assert layout["minimum_sequence_font_pt"] == 8
    assert layout["pages"][0]["state_ids"] == ["s0", "s1"]
    assert layout["pages"][1]["state_ids"] == ["s2", "s3"]
    assert paginate_atlas(route()) == (pages, layout)


def test_invalid_row_order_is_rejected_instead_of_clipped():
    with pytest.raises(ValueError, match="order"):
        paginate_atlas(route().replace(b'data-atlas-y="650"', b'data-atlas-y="40"'))


def test_single_tall_stage_expands_the_page_without_splitting_the_molecule():
    large = route().replace(b"0 0 2200 2450", b"0 0 2200 4450")
    pages, layout = paginate_atlas(large)
    assert len(pages) == 3
    assert layout["pages"][-1]["state_ids"] == ["s3"]
    assert layout["pages"][-1]["height_pt"] > 792
