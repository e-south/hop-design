"""Compact inspection is a browser transport, never a second public query."""

from xml.etree import ElementTree as ET

from hop_design.api import _InspectionProjection
from hop_design.commands.design.inspection import DesignInspectionSession
from tests.integration.test_atlas_edition import captured_choices  # noqa: F401


def test_compact_map_preserves_public_query_selection_and_shared_coordinates(
    captured_choices,  # noqa: F811
    tmp_path,
):
    edition = captured_choices.freeze(tmp_path / "edition", include_landscape=True)
    session = DesignInspectionSession(edition, tmp_path / "browser")
    try:
        public = edition.query()
        compact = session.response(session.state, format="compact-v1")
        assert compact["families"] is None
        assert compact["presentation"]["display_axes"] == [
            "open_side_paired_positions",
            "left_end_word",
            "left_gap",
            "right_gap",
            "right_end_word",
            "foldback_arm_bp",
            "loop_nt",
        ]
        assert "choices" not in compact and "similarity" not in compact["plots"]
        members = compact["compact"]["members"]
        assert members == [p["materialized_realization_id"] for p in public["paths"]]
        assert compact["map_index"]["schema"] == "hop.inspection-map/v1"
        assert {p[0] for p in compact["map_index"]["points"]} == set(range(len(members)))
        comparison = compact["map_index"]["comparison"]
        fitted = edition.landscape()
        assert comparison["basis"] == fitted.basis.model_dump(
            mode="json", exclude={"comparison_keys"}
        )
        recorded = {row.identity: row for row in fitted.preparations}
        for column in comparison["columns"]:
            block, key = column["key"].split(".")
            for i, identity in enumerate(members):
                value = column["dictionary"][column["indices"][i]]
                if column.get("encoding") == "contacts":
                    value = tuple(comparison["contacts"][j] for j in value)
                descriptor = recorded[identity]
                expected = {
                    "shape": descriptor.compared_shape,
                    "sequences": descriptor.compared_sequences,
                    "interfaces": descriptor.interfaces,
                }[block]
                assert value == expected[key]
        svg = ET.fromstring(edition.plot_svg_bytes(view="similarity"))
        positions = {
            g.attrib["data-preparation"]: [
                float(c.attrib[k]) - float(g.attrib[offset])
                for k, offset in (("cx", "data-display-dx"), ("cy", "data-display-dy"))
            ]
            for g in svg.iter()
            if "data-preparation" in g.attrib
            for c in g
            if c.tag.endswith("circle")
        }
        for index, x, y in compact["map_index"]["points"]:
            # Printed member expansions carry explicit display offsets; the
            # interactive overview uses their same underlying comparison position.
            assert [x, y] == positions[members[index]]
        axes = (session.root / compact["plots"]["parameters"].removeprefix("/files/")).read_bytes()
        assert b"data-members=" not in axes
        identity = members[0]
        selected = session.response(
            lambda: session.select(
                {"token": compact["token"], "materialized_realization_id": identity}
            ),
            cohort=compact["cohort"],
            format="compact-v1",
        )
        assert selected["cohort_unchanged"]
        assert "compact" not in selected and "map_index" not in selected
        assert selected["selection"] == edition.select(identity)
        assert selected["view_receipt"]["schema"] == "hop.atlas-view/v4"
        assert selected["view_receipt"]["presentation"] == compact["presentation"]
        assert edition.query() == public
        assert session.state()["choices"] == _InspectionProjection.display(public)
        assert session.state()["families"] is not None
    finally:
        session.close()
