"""Recorded contacts, cleavage locations and achieved interfaces survive presentation."""

import json

import pytest

from hop_design.design.construction.projections.inspection import project_molecular_inspection
from hop_design.export.construction.molecular.inspection import _points


@pytest.fixture(scope="module")
def inspected_route(loop_pool):
    pool = loop_pool
    return pool._routes[0][1]


def test_route_scene_composition_keeps_native_elements_until_export(inspected_route, monkeypatch):
    """Composing a route must not serialize and reparse each completed scene."""
    from xml.dom import minidom
    from xml.etree import ElementTree as ET

    from hop_design.design.construction.projections.atlas import project_molecular_atlas
    from hop_design.export.construction.molecular.atlas_layout import atlas_scenes

    atlas = project_molecular_atlas(inspected_route)

    def forbid_serialization(*args, **kwargs):
        pytest.fail("Keep composed molecular scenes as elements until the export boundary")

    monkeypatch.setattr(ET, "tostring", forbid_serialization)
    monkeypatch.setattr(minidom.Element, "toxml", forbid_serialization)
    scenes = atlas_scenes(atlas, presentation="assembly")
    assert len(scenes.scenes) == len(atlas.states)
    for index, (root, width, height, _) in scenes.scenes.items():
        state = atlas.states[index].state
        actual = {
            (node.get("data-strand-id"), int(node.attrib["data-base-index"]))
            for node in root.iter()
            if node.get("data-base-index") is not None
        }
        expected = {
            (strand.strand_id, position)
            for strand in state.molecules
            for position in range(len(strand.sequence))
        }
        assert actual == expected
        assert width > 0 and height > 0


@pytest.mark.parametrize("phase", ["cleaved_duplex", "annealed_complex"])
def test_associated_fragments_keep_pairing_columns(inspected_route, phase):
    projection = project_molecular_inspection(inspected_route, phase)
    points = _points(projection)
    for pair in projection.state.pairings:
        assert (
            points[pair.left_strand_id, pair.left_index][0]
            == points[pair.right_strand_id, pair.right_index][0]
        )


def test_unpaired_hairpin_handles_bend_then_resume_parallel_without_moving_contacts(
    inspected_route,
):
    projection = project_molecular_inspection(inspected_route, "adapter_ligated")
    points = _points(projection)
    paired = {p.left_index for p in projection.state.pairings} | {
        p.right_index for p in projection.state.pairings
    }
    strand = projection.state.molecules[0]
    start, end = min(paired), max(paired)
    assert start > 0 or end < len(strand.sequence) - 1
    long_handles = 0
    for i, anchor in [(0, start), (len(strand.sequence) - 1, end)]:
        if i == anchor:
            continue
        x, y = points[strand.strand_id, i]
        ax, ay = points[strand.strand_id, anchor]
        count = abs(i - anchor)
        if count <= 5:
            assert abs(x - ax) == pytest.approx(abs(y - ay))
        else:
            long_handles += 1
            sign = 1 if i > anchor else -1
            bend = points[strand.strand_id, anchor + sign * 5]
            after = points[strand.strand_id, anchor + sign * 6]
            assert y == pytest.approx(bend[1])
            assert after[1] == pytest.approx(bend[1])
            assert abs(after[0] - bend[0]) == pytest.approx(16)
            assert abs(bend[0] - ax) == pytest.approx(abs(bend[1] - ay))
    assert long_handles
    for pair in projection.state.pairings:
        assert (
            points[pair.left_strand_id, pair.left_index][0]
            == points[pair.right_strand_id, pair.right_index][0]
        )


def test_operation_annotations_are_stage_bound(inspected_route):
    source = project_molecular_inspection(inspected_route, "source_material")
    assert source.operations == ()
    duplex = project_molecular_inspection(inspected_route, "duplex")
    nicked = project_molecular_inspection(inspected_route, "cleaved_duplex")
    assert len(duplex.operations) == len(nicked.operations) == 2
    assert sum(len(o.cuts) for o in duplex.operations) == 2
    assert {o.timing for o in duplex.operations} == {"planned"}
    assert {o.timing for o in nicked.operations} == {"applied"}
    release = project_molecular_inspection(inspected_route, "hairpin_pcr_duplex")
    assert len(release.operations) == 2
    assert sum(len(o.cuts) for o in release.operations) == 4
    endpoint = project_molecular_inspection(inspected_route, "endpoint")
    assert endpoint.operations == ()
    assert len(endpoint.interfaces) == 2
    assert {g.distance_bp for g in endpoint.interfaces} == {6}
    assert all(len(g.overhang) == 4 for g in endpoint.interfaces)
    assert json.loads(endpoint.model_dump_json())["state"] == json.loads(
        inspected_route.construction_program.states[-1].model_dump_json()
    )


def test_recognition_footprints_persist_without_inventing_operations(inspected_route):
    from hop_design.export.construction.molecular.inspection import render_molecular_inspection

    projections = {
        phase: project_molecular_inspection(inspected_route, phase)
        for phase in ("source_ssdna", "duplex", "adapter_annealed", "adapter_ligated", "endpoint")
    }
    sites = {
        phase: {site.site_id: site for site in projection.recognition_sites}
        for phase, projection in projections.items()
    }
    left, right = "complete-end-generation-left", "complete-end-generation-right"
    assert sites["source_ssdna"][left].recognition
    assert sites["source_ssdna"][right].presence == "not_yet_present"
    for phase in ("duplex", "adapter_annealed", "adapter_ligated"):
        assert sites[phase][left].recognition
    assert sites["adapter_annealed"][right].recognition
    assert sites["endpoint"][left].presence == "removed"
    assert sites["endpoint"][right].presence == "removed"
    assert projections["adapter_ligated"].operations == ()
    assert len(sites["adapter_ligated"]) == 4
    svg = render_molecular_inspection(projections["adapter_ligated"]).decode()
    assert 'data-site-id="complete-end-generation-left"' in svg
    assert 'data-site-id="complete-end-generation-right"' in svg
    assert "data-cut=" not in svg


def test_unchanged_processing_view_keeps_each_base_its_own_anchor(inspected_route):
    from hop_design.design.construction.projections.inspection_correspondence import (
        inspection_correspondence,
    )

    state = project_molecular_inspection(inspected_route, "duplex").state
    correspondence = inspection_correspondence(inspected_route, state, inspected_route, state)
    assert all(
        link.reference == link.target and link.relation == "retained"
        for link in correspondence.links
    )
    assert len(correspondence.links) == sum(len(s.sequence) for s in state.molecules)


@pytest.mark.parametrize(
    "phase",
    ["duplex", "cleaved_duplex", "denatured_fragments", "annealed_complex", "adapter_annealed"],
)
def test_layout_is_independent_of_fragment_and_contact_order(inspected_route, phase):
    projection = project_molecular_inspection(inspected_route, phase)

    # Presentation seam only: sealed route admission is tested separately.
    # Reorder tuples without claiming a new admitted molecular identity.
    def permute(state):
        return state.model_copy(
            update={
                "molecules": tuple(reversed(state.molecules)),
                "pairings": tuple(reversed(state.pairings)),
            }
        )

    reordered = projection.model_copy(
        update={
            "state": permute(projection.state),
            "layout_frame": permute(projection.layout_frame) if projection.layout_frame else None,
        }
    )
    assert _points(reordered) == _points(projection)
    if phase == "denatured_fragments":
        assert reordered.state.pairings == ()
        assert reordered.layout_frame is not None


@pytest.mark.parametrize("phase", ["denatured_fragments", "selected_fragments"])
def test_separated_fragments_remain_registered_to_the_cleaved_source(inspected_route, phase):
    from hop_design.export.construction.molecular.inspection import render_molecular_inspection

    cleaved = project_molecular_inspection(inspected_route, "cleaved_duplex")
    separated = project_molecular_inspection(inspected_route, phase)
    before, after = _points(cleaved), _points(separated)
    origins = {
        (b.origin_id, b.origin_strand, b.origin_index): before[m.strand_id, b.product_index]
        for m in cleaved.state.molecules
        for b in m.lineage
    }
    for molecule in separated.state.molecules:
        for base in molecule.lineage:
            old = origins[base.origin_id, base.origin_strand, base.origin_index]
            new = after[molecule.strand_id, base.product_index]
            assert new[0] == pytest.approx(old[0])
            assert 8 <= abs(new[1] - old[1]) <= 24
    assert separated.state.pairings == ()
    assert b'data-edge-kind="pair"' not in render_molecular_inspection(separated)


def test_reverse_operations_and_terminal_boundaries_are_literal(inspected_route):
    from hop_design.design.construction.projections.inspection_annotations import boundary
    from hop_design.export.construction.molecular.inspection import render_molecular_inspection
    from hop_design.export.construction.molecular.inspection_overlays import inspection_overlays
    from hop_design.models.construction.projections.inspection_annotations import InspectionCut

    projection = project_molecular_inspection(inspected_route, "hairpin_pcr_duplex")
    assert {op.orientation for op in projection.operations} == {"forward", "reverse"}
    svg = render_molecular_inspection(projection).decode()
    assert 'data-orientation="forward"' in svg and 'data-orientation="reverse"' in svg
    assert 'data-display-direction="right"' in svg and 'data-display-direction="left"' in svg
    strand = projection.state.molecules[0]
    start = boundary(projection.state, strand.strand_id, 0)
    end = boundary(projection.state, strand.strand_id, len(strand.sequence))
    assert start.before is None and start.after.index == 0
    assert end.after is None and end.before.index == len(strand.sequence) - 1
    with pytest.raises(ValueError, match="outside"):
        boundary(projection.state, strand.strand_id, len(strand.sequence) + 1)
    # Rendering edge case only; no new biochemical route is asserted.
    operation = projection.operations[0].model_copy(
        update={
            "cuts": (
                InspectionCut(strand="reference", precursor_offset=0, boundary=start),
                InspectionCut(
                    strand="complement", precursor_offset=len(strand.sequence), boundary=end
                ),
            )
        }
    )
    edge_view = projection.model_copy(update={"operations": (operation,)})
    assert 'data-boundary="0"' in inspection_overlays(edge_view, _points(edge_view))
    for op in projection.operations:
        for cut in op.cuts:
            index = cut.boundary.after.index
            assert index == (
                cut.precursor_offset
                if cut.strand == "reference"
                else len(strand.sequence) - cut.precursor_offset
            )


def test_projection_rejects_annotation_addresses_outside_displayed_state(inspected_route):
    from hop_design.models.construction.projections.inspection import MolecularStateInspection

    value = json.loads(project_molecular_inspection(inspected_route, "duplex").model_dump_json())
    value["operations"][0]["recognition"][0]["index"] = 100000
    with pytest.raises(ValueError, match="annotation"):
        MolecularStateInspection.model_validate_json(json.dumps(value))


def test_scene_carries_fitted_regions_and_addressed_edges(inspected_route):
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.molecular.inspection import render_molecular_inspection

    projection = project_molecular_inspection(inspected_route, "hairpin")
    root = ET.fromstring(render_molecular_inspection(projection))
    regions = root.findall(".//*[@data-region-fill]")
    assert {r.attrib["data-region-fill"] for r in regions} >= {
        "stem",
        "closing",
        "loop",
        "assembly",
    }
    assert all(r.attrib.get("data-members") for r in regions)
    assert {r.attrib["fill"] for r in regions if r.attrib["data-region-fill"] == "stem"} == {
        "#B95300"
    }
    assert all(r.tag.endswith("}path") and r.get("data-path-members") for r in regions)
    edges = root.findall(".//*[@data-edge-kind]")
    assert sum(e.attrib["data-edge-kind"] == "pair" for e in edges) == len(
        projection.state.pairings
    )
    assert all(e.attrib.get("data-from") and e.attrib.get("data-to") for e in edges)
    bases = root.findall(".//*[@data-base-index]")
    assert all(b.find("{http://www.w3.org/2000/svg}rect").attrib["fill"] == "none" for b in bases)


def test_persistent_site_orientation_follows_its_folded_strand(inspected_route):
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.molecular.inspection import render_molecular_inspection

    view = project_molecular_inspection(inspected_route, "hairpin")
    root = ET.fromstring(render_molecular_inspection(view))
    right = root.find('.//*[@data-site-id="complete-end-generation-right"]')
    # The reverse-binding release site lies on the return arm, which is drawn
    # right-to-left. Its recognition orientation on this page therefore points right.
    assert right.attrib["data-display-direction"] == "right"
