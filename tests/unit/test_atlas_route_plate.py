"""Native route plates preserve layout; fixed-width pages preserve readable bases."""

import json
from xml.etree import ElementTree as ET

import pytest

from hop_design.design.construction.packets.atlas import MolecularAtlasPacket
from hop_design.export.construction.molecular.printing.atlas import native_route_plate
from hop_design.export.publication import ProtectedRoot


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


def inventory(raw):
    return [
        (e.attrib, "".join(e.itertext()))
        for e in ET.fromstring(raw).iter()
        if e.get("data-base-index") is not None or e.get("data-atlas-input")
    ]


class RoutePlatePacket(MolecularAtlasPacket):
    _packet_schema = "hop.test-route-plate/v1"


def packet(root):
    root.mkdir()
    (root / "source.svg").write_bytes(route())
    result = RoutePlatePacket._create({"projection.svg": route()}, {}, "# Recorded route\n")
    object.__setattr__(result, "_roots", (ProtectedRoot.capture(root),))
    return result


def test_native_plate_sizes_the_existing_two_column_route_without_reflow():
    plate, layout = native_route_plate(route())
    original, printed = ET.fromstring(route()), ET.fromstring(plate)
    assert printed.get("viewBox") == original.get("viewBox") == "0 0 2400 3000"
    assert printed.get("data-atlas-layout") == "columns-with-finish"
    assert float(printed.get("width").removesuffix("pt")) == 1200
    assert float(printed.get("height").removesuffix("pt")) == 1500
    assert inventory(plate) == inventory(route())
    assert layout["minimum_sequence_font_pt"] == 8
    assert layout["scale_pt_per_unit"] == 0.5
    assert layout["preserves_source_viewbox"] is True
    assert layout["source_viewbox"] == "0 0 2400 3000"
    assert layout["reference_width_pt"] == 504
    assert layout["reference_sequence_font_pt"] == pytest.approx(3.36)
    assert not layout["reference_width_meets_sequence_minimum"]
    assert native_route_plate(route()) == (plate, layout)


@pytest.mark.parametrize(
    "old,new",
    [
        (b'data-atlas="true"', b'data-atlas="false"'),
        (b"0 0 2400 3000", b"1 0 2400 3000"),
        (b"0 0 2400 3000", b"0 0 nan 3000"),
        (b'font-size="16"', b'font-size="0"'),
        (b'font-size="16"', b'font-size="nan"'),
    ],
)
def test_native_plate_rejects_invalid_generated_atlas(old, new):
    with pytest.raises(ValueError):
        native_route_plate(route().replace(old, new))


@pytest.mark.parametrize("value", ["nan", "inf", "0", "-1"])
def test_native_plate_rejects_one_bad_font_after_a_valid_base(value):
    root = ET.fromstring(route())
    text = list(root.iter("{http://www.w3.org/2000/svg}text"))
    text[-1].set("font-size", value)
    with pytest.raises(ValueError):
        native_route_plate(ET.tostring(root))


def test_preview_write_stays_byte_identical_without_print_work(tmp_path, monkeypatch):
    from hop_design.design.construction.packets import atlas as atlas_module

    def unexpected(*args):
        raise AssertionError("Preview export must not render print plates")

    monkeypatch.setattr(atlas_module, "native_route_plate", unexpected)
    source = packet(tmp_path / "source")
    expected = dict(source._files)
    source.write(tmp_path / "preview", print_pages=False)
    assert {p.name: p.read_bytes() for p in (tmp_path / "preview").iterdir()} == expected


def test_print_export_supplies_native_plate_and_existing_continuation_pages(tmp_path):
    source = packet(tmp_path / "source")
    source.write(tmp_path / "print")
    target = tmp_path / "print"
    assert (target / "projection.svg").read_bytes() == route()
    assert (target / "route-plate.pdf").read_bytes().startswith(b"%PDF")
    assert (target / "projection.pdf").read_bytes().startswith(b"%PDF")
    assert list((target / "pages").glob("*.svg"))
    assert inventory((target / "route-plate.svg").read_bytes()) == inventory(route())
    plate = json.loads((target / "route-plate-layout.json").read_bytes())
    pages = json.loads((target / "print-layout.json").read_bytes())
    assert plate["width_pt"] == 1200
    assert pages["page_width_pt"] == 504
    assert pages["minimum_sequence_font_pt"] == 8
    assert "route-plate.pdf" in (target / "report.md").read_text()
    artifacts = json.loads((target / "manifest.json").read_bytes())["artifacts"]
    assert {"route-plate.svg", "route-plate.pdf", "route-plate-layout.json"} <= artifacts.keys()
