"""A controlled series requires molecular agreement, not identical manufacturing inputs."""

import json

import pytest

from hop_design import construction
from tests.integration.test_construction_comparison_projection import loop_series as loop_series
from tests.integration.test_construction_family import family_path
from tests.integration.test_construction_family_report import family_capture as family_capture
from tests.integration.test_construction_set import set_path
from tests.integration.test_family_authoring import brief_path

CONTROLS = ["non_loop_sequences", "regional_contacts", "regional_joins"]


def test_selected_series_can_require_surrounding_molecular_control(tmp_path, loop_series):
    path = set_path(tmp_path, loop_series)
    data = json.loads(path.read_text())
    data["shared_properties"] += CONTROLS
    path.write_text(json.dumps(data))
    packet = construction.select_construction_set(path)
    summary = json.loads(packet.json_bytes)
    checks = {c["property"]: c for c in summary["comparison_controls"]}
    assert all(checks[key]["status"] == "required_and_verified" for key in CONTROLS)
    packet.write(tmp_path / "controlled")
    comparison = json.loads((tmp_path / "controlled/comparisons/loop4.json").read_text())
    assert comparison["changed_material_roles"] == [
        "source_ssdna",
        "source_materialization_reverse_primer",
    ]
    assert (
        construction.select_construction_set(tmp_path / "controlled/set.json").json_bytes
        == packet.json_bytes
    )


def test_authoring_keeps_molecular_controls_as_explicit_family_requirements(tmp_path):
    path = brief_path(tmp_path)
    data = json.loads(path.read_text())
    data["hold"] += CONTROLS
    path.write_text(json.dumps(data))
    authored = construction.author_construction_family(path)
    output = authored.write(tmp_path / "authored")
    family = json.loads((output / "family.json").read_text())
    assert set(CONTROLS) <= set(family["shared_properties"])
    assert "No molecular search has run" in authored.report_text


def test_family_keeps_complete_but_nonmatching_molecules_out_of_shared_display(tmp_path):
    path = family_path(tmp_path)
    data = json.loads(path.read_text())
    data["members"] = [
        {"name": "reference", "loop_nt": 3, "loop_side_paired_bp": 7},
        {"name": "longer", "loop_nt": 3, "loop_side_paired_bp": 8},
    ]
    data["base_request"]["foldback"]["geometry"]["annealing_arm_lengths_bp"] = [7, 8]
    data["shared_properties"] += CONTROLS
    path.write_text(json.dumps(data))
    packet = construction.execute_construction_family(path, continuation="sole-witness")
    saved = packet.write(tmp_path / "executed")
    result = json.loads(packet.json_bytes)
    assert [m["outcome"]["status"] for m in result["members"]] == ["complete", "complete"]
    assert result["display_order"] == ["reference"]
    assert {
        d["property"] for d in result["members"][1]["choices"][0]["shared_property_differences"]
    } >= {"non_loop_sequences", "regional_contacts"}
    report = json.loads(construction.project_construction_family_report(saved).json_bytes)
    controls = {c["property"]: c for c in report["family_controls"]}
    assert controls["non_loop_sequences"]["status"] == "different"
    request = {
        "schema": "hop.construction-set/v1",
        "baseline": "reference",
        "members": [
            {
                "name": m["name"],
                "bundle_path": str(saved / "members" / m["name"] / "outcome/construction"),
                "selection_path": str(saved / m["choices"][0]["selection"]),
            }
            for m in result["members"]
        ],
        "shared_properties": CONTROLS,
        "compared_properties": ["loop_side_paired_bp"],
    }
    (tmp_path / "set.json").write_text(json.dumps(request))
    with pytest.raises(ValueError, match="non_loop_sequences"):
        construction.select_construction_set(tmp_path / "set.json").write(tmp_path / "invalid-set")
    assert not (tmp_path / "invalid-set").exists()
    # A set with weaker controls cannot silently bypass its originating family's requirements.
    request["shared_properties"] = []
    (tmp_path / "set.json").write_text(json.dumps(request))
    with pytest.raises(ValueError, match=r"family.*shared"):
        construction.project_construction_family_report(saved, selection=tmp_path / "set.json")


def test_report_distinguishes_selected_requirements_from_family_observations(
    family_capture, tmp_path
):
    data = json.loads((family_capture / "set.json").read_text())
    for member in data["members"]:
        member["bundle_path"] = str(family_capture / member["bundle_path"])
        member["selection_path"] = str(family_capture / member["selection_path"])
    data["shared_properties"] += CONTROLS
    path = tmp_path / "required.json"
    path.write_text(json.dumps(data))
    report = construction.project_construction_family_report(
        family_capture / "executed", selection=path
    )
    summary = json.loads(report.json_bytes)
    family = {c["property"]: c for c in summary["family_controls"]}
    selected = {c["property"]: c for c in summary["selected_controls"]}
    assert family["non_loop_sequences"]["required"] is False
    assert family["non_loop_sequences"]["status"] == "not_assessed"  # Failed member has no product.
    assert selected["non_loop_sequences"]["status"] == "required_and_verified"
    assert "short-primer" in family["non_loop_sequences"]["unassessed_members"]


def test_control_assessment_never_equates_unknown_evidence():
    from hop_design.design.construction.families.controls import assess_controls

    checks = assess_controls(
        {"a": {"non_loop_sequences": None}, "b": {"non_loop_sequences": None}}, "a", CONTROLS
    )
    assert len([c for c in checks if c.property in CONTROLS]) == 3
    assert all(c.status == "not_assessed" for c in checks if c.property in CONTROLS)


def test_single_selection_does_not_establish_between_member_agreement(tmp_path, loop_series):
    path = set_path(tmp_path, loop_series)
    data = json.loads(path.read_text())
    data["members"] = data["members"][:1]
    data["compared_properties"] = []
    path.write_text(json.dumps(data))
    packet = construction.select_construction_set(path)
    checks = json.loads(packet.json_bytes)["comparison_controls"]
    assert all(c["status"] == "not_assessed" for c in checks)
    assert "Single selected molecule" in packet.report_text
