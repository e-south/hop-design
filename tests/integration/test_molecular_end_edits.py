"""End placement remains a finite conditional request, including negative outcomes."""

import json
from pathlib import Path

from hop_design import construction
from tests.integration.test_molecular_edits import loop_request


def test_end_edit_preserves_pairing_and_exposes_every_distance(tmp_path):
    path = loop_request(tmp_path)
    value = json.loads(path.read_bytes())
    value["max_branches"] = 3
    path.write_text(json.dumps(value))
    edit = construction.author_molecular_edit(
        path,
        end_placements=((0, 0), (3, 3), (6, 6)),
        basal_nick_enzyme_ids=("example:enzyme/nb.bsrdi@1",),
    )
    root = edit.write(tmp_path / "intent")
    preview = json.loads(edit.json_bytes)
    assert preview["status"] == "ready"
    compiled = json.loads((root / "compiled-request.json").read_bytes())
    assert compiled["product"]["basal"]["geometry"] == value["product"]["basal"]["geometry"]
    assert len(compiled["required_targets"]) == 3
    result = construction.execute_molecular_edit(root / "edit.json")
    summary = json.loads(result.json_bytes)
    placement = summary["end_placement_comparison"]
    assert placement["closest_complete_examined"] == {"left_bp": 6, "right_bp": 6}
    assert placement["global_minimum"] == "not_assessed"
    assert len(placement["requested"]) == 3
    assert len(summary["branches"]) == 3
    assert any(b["complete_preparations"] == 0 for b in summary["branches"])


def test_end_edit_keeps_forbidden_methods_and_wrong_stage_visible(tmp_path):
    path = loop_request(tmp_path)
    value = json.loads(path.read_bytes())
    value["product"]["basal"]["enzymes"]["reserved_enzyme_ids"] = ["example:enzyme/nt.bpu10i@1"]
    path.write_text(json.dumps(value))
    edit = construction.author_molecular_edit(
        path,
        end_placements=((6, 6),),
        basal_nick_enzyme_ids=("example:enzyme/nt.bpu10i@1",),
    )
    summary = json.loads(edit.json_bytes)
    assert summary["status"] == "conflicting_requirements"
    assert "reserved_enzyme_ids" in str(summary["conflicts"])


def test_equal_dimensions_do_not_hide_retained_nickase_sequence_changes(tmp_path):
    edit = construction.author_molecular_edit(
        Path("examples/molecular-editing/request.json"),
        end_placements=((6, 6),),
        basal_nick_enzyme_ids=("example:enzyme/nb.bsrdi@1", "example:enzyme/nb.btsi@1"),
    ).write(tmp_path / "edit")
    packet = construction.execute_molecular_edit(edit / "edit.json")
    root = packet.write(tmp_path / "result")
    summary = json.loads(packet.json_bytes)
    assert len(summary["options"]) == 2
    for option, name in zip(summary["options"], ("Nb.BsrDI", "Nb.BtsI"), strict=True):
        assert name in (root / option["sequence_drawing"]).read_text()
    a, b = [json.loads((root / o["sequence_view"]).read_bytes()) for o in summary["options"]]
    assert a["portrait"]["loop_nt"] == b["portrait"]["loop_nt"]
    assert b["pairing_relationships_unchanged"]
    assert set(b["changed_material_roles"]) == {"source_ssdna", "ligation_adapter"}
    substitutions = [
        c
        for r in b["endpoint_sequence_differences"]
        for c in r["columns"]
        if c["kind"] == "substitution"
    ]
    assert {(c["reference_base"], c["observed_base"]) for c in substitutions} == {
        ("A", "G"),
        ("T", "C"),
    }
