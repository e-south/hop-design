"""One compact vector viewport retains every product and its exact membership."""

import json
from xml.etree import ElementTree as ET

from hop_design.design.construction.navigation.molecular_groups import molecular_families
from hop_design.export.construction.survey.families import render_molecular_families
from tests.unit.test_molecular_families import choices, path


def test_mosaic_retains_product_identity_and_preparation_counts():
    atlas = molecular_families(
        choices([path("a", "one"), path("b", "one"), path("c", "two")]), stage="hairpin"
    )
    svg = ET.fromstring(render_molecular_families(atlas, selected_identity="b"))
    nodes = [g for g in svg.iter() if g.get("data-products")]
    assert {i for g in nodes for i in json.loads(g.get("data-products"))} == {"one", "two"}
    selected = [g for g in nodes if g.get("data-selected") == "true"]
    assert len(selected) == 1
    assert json.loads(selected[0].get("data-products")) == ["one"]
    assert svg.get("data-layout") == "mosaic"
    filters = [g for g in svg.iter() if g.get("data-family-ids")]
    assert len(filters) == 1
    assert json.loads(filters[0].get("data-family-ids")) == [atlas["families"][0]["identity"]]
    assert filters[0].get("role") == "button" and filters[0].get("tabindex") == "0"
    assert svg.get("height", "").endswith("in")
    assert float(svg.get("viewBox").split()[2]) / float(svg.get("viewBox").split()[3]) > 2


def test_feature_map_aggregates_coincident_products_without_inventing_coordinates():
    atlas = molecular_families(
        choices([path("a", "one"), path("b", "two"), path("c", "three", loop=6, extension=5)]),
        stage="hairpin",
    )
    svg = ET.fromstring(render_molecular_families(atlas))
    nodes = [g for g in svg.iter() if g.get("data-products")]
    assert len(nodes) == 2
    assert {tuple(json.loads(g.get("data-products"))) for g in nodes} == {
        ("one", "two"),
        ("three",),
    }
    assert svg.get("data-layout") == "feature_map"
    assert svg.get("data-x-parameter") == "loop_nt"
    assert {
        f
        for g in svg.iter()
        if g.get("data-family-ids")
        for f in json.loads(g.get("data-family-ids"))
    } == {f["identity"] for f in atlas["families"]}


def test_composed_family_figure_uses_product_symbols_not_trace_or_search_symbols():
    from hop_design.export.construction.survey.figure import compose_figure

    atlas = molecular_families(choices([path("a", "one")]), stage="hairpin")
    key = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 100" />'
    drawing = compose_figure(key, render_molecular_families(atlas), {"axes": []})
    text = " ".join(ET.fromstring(drawing).itertext())
    assert "dark outline: selected" in text
    assert "Orange trace" not in text and "dotted: unresolved" not in text
