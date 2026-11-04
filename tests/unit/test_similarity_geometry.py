"""Interactive and exported maps locate the same exact preparations."""

from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

from hop_design.export.construction.survey.similarity import (
    landscape_geometry,
    render_molecular_landscape,
)


def test_shared_geometry_retains_coincident_members_and_exported_positions():
    landscape = SimpleNamespace(
        digest="map",
        preparations=tuple(
            SimpleNamespace(identity=i, comparison_key="same", sequences={"loop": "AAAA"})
            for i in ("second", "first")
        ),
        coordinates=(SimpleNamespace(comparison_key="same", x=0.0, y=0.0),),
    )
    geometry = landscape_geometry(landscape)
    points = geometry["points"]
    assert [p["identity"] for p in points] == ["first", "second"]
    assert all(p["molecular"] == [0.0, 0.0] and p["coincident"] == 2 for p in points)
    assert points[0]["x"] == points[1]["x"]
    assert points[0]["y"] == points[1]["y"]
    svg = ET.fromstring(render_molecular_landscape(landscape, eligible={"first"}))
    assert not [e for e in svg if e.tag.endswith("path")]
    groups = {g.attrib["data-preparation"]: g for g in svg.iter() if "data-preparation" in g.attrib}
    for point in points:
        circle = next(n for n in groups[point["identity"]] if n.tag.endswith("circle"))
        assert float(circle.attrib["cx"]) == pytest.approx(point["x"])
        assert float(circle.attrib["cy"]) == pytest.approx(point["y"])
    assert groups["first"].attrib["data-eligible"] == "true"
    assert groups["second"].attrib["data-eligible"] == "false"
    assert groups["first"].attrib["data-coincident-count"] == "2"
    assert "share a position" in "".join(svg.itertext())


def test_selected_coincident_preparation_is_painted_last_without_moving_its_position():
    landscape = SimpleNamespace(
        digest="map",
        preparations=tuple(
            SimpleNamespace(identity=i, comparison_key="same", sequences={"loop": "AAAA"})
            for i in ("second", "first")
        ),
        coordinates=(SimpleNamespace(comparison_key="same", x=0.0, y=0.0),),
    )
    points = landscape_geometry(landscape)["points"]
    assert [p["identity"] for p in points] == ["first", "second"]
    assert all([p["x"], p["y"]] == p["center"] for p in points)
    assert all(p["offset"] == [0, 0] and p["coincident"] == 2 for p in points)
    svg = ET.fromstring(
        render_molecular_landscape(
            landscape, eligible={"first", "second"}, selected_identity="first"
        )
    )
    groups = [e for e in svg if e.get("data-preparation")]
    assert groups[-1].get("data-preparation") == "first"
    assert groups[-1].get("data-selected") == "true"


def test_exported_cloud_preserves_density_and_emphasizes_only_the_selected_preparation():
    landscape = SimpleNamespace(
        digest="map",
        preparations=tuple(
            SimpleNamespace(identity=i, comparison_key="same", sequences={"loop": "AAAA"})
            for i in ("selected", "eligible", "excluded")
        ),
        coordinates=(SimpleNamespace(comparison_key="same", x=0.0, y=0.0),),
    )
    svg = ET.fromstring(
        render_molecular_landscape(
            landscape, eligible={"selected", "eligible"}, selected_identity="selected"
        )
    )
    marks = {
        group.get("data-preparation"): group.find("{http://www.w3.org/2000/svg}circle")
        for group in svg
        if group.get("data-preparation")
    }
    selected, eligible, excluded = (marks[k] for k in ("selected", "eligible", "excluded"))
    assert selected is not None and eligible is not None and excluded is not None
    assert 0 < float(eligible.get("fill-opacity", "1")) < 0.5
    assert eligible.get("stroke") == "none"
    assert float(eligible.get("r")) < float(selected.get("r"))
    assert float(selected.get("fill-opacity", "1")) == 1
    assert excluded.get("fill") == "none"
    assert 0 < float(excluded.get("stroke-opacity", "1")) < 0.5
    assert len({(m.get("cx"), m.get("cy")) for m in marks.values()}) == 1
