"""Locate all conflicting declarations without searching or relaxing the request."""

import json
from xml.etree import ElementTree

from hop_design import construction
from tests.integration.test_family_authoring import brief_path


def test_preview_locates_domain_and_requirement_conflicts_and_draws_intent(tmp_path):
    path = brief_path(tmp_path)
    brief = json.loads(path.read_text())
    brief["geometry_permissions"]["loop_nt"] = [4]
    path.write_text(json.dumps(brief))
    base = tmp_path / brief["base_request"]
    data = json.loads(base.read_text())
    data["whole_route_constraints"]["hairpin_scaffold"] = {"loop_nt": {"minimum": 4, "maximum": 4}}
    base.write_text(json.dumps(data))
    before = base.read_bytes()
    packet = construction.author_construction_family(path)
    summary = json.loads(packet.json_bytes)
    conflicts = summary["members"][0]["conflicts"]
    assert {c["declaration_path"] for c in conflicts} == {
        "base_request.foldback.geometry.loop_lengths_nt",
        "base_request.whole_route_constraints.hairpin_scaffold.loop_nt",
    }
    assert all(c["requested"] == 3 and c["edit_options"] for c in conflicts)
    assert summary["members"][1]["conflicts"] == []
    assert base.read_bytes() == before
    output = packet.write(tmp_path / "preview")
    drawing = (output / "preview.svg").read_text()
    ElementTree.fromstring(drawing)
    assert "Requested geometry" in drawing
    assert "No molecular search" in drawing
    assert "loop3" in drawing and "3 nt" in drawing
    assert "Shared requirements" in drawing
    assert "Material permissions" in drawing
    assert not (output / "members/loop3/request.json").exists()
    assert "base_request.foldback.geometry.loop_lengths_nt" in packet.report_text
