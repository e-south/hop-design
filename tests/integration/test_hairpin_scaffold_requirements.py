"""Hard scaffold ranges constrain the achieved molecule, not source coordinates."""

import json

import pytest

from hop_design import construction
from tests.integration.test_request_execution import request_path


@pytest.mark.parametrize("open_side,expected", [(17, "complete"), (10, "infeasible")])
def test_complete_request_enforces_exact_and_allowed_scaffold_dimensions(
    tmp_path, open_side, expected
):
    path = request_path(tmp_path)
    request = json.loads(path.read_text())
    request["whole_route_constraints"]["hairpin_scaffold"] = {
        "open_side_paired_positions": {"minimum": open_side, "maximum": open_side},
        "loop_side_paired_bp": {"minimum": 5, "maximum": 6},
        "loop_nt": {"minimum": 3, "maximum": 5},
    }
    path.write_text(json.dumps(request))
    prepared = construction.prepare_construction_request(path)
    assert "Hairpin scaffold requirements" in prepared.report_text
    execution = construction.execute_construction_request(
        path, design_id="scaffold-requirements", continuation="sole-witness"
    )
    execution.write(tmp_path / "run")
    summary = json.loads(execution.json_bytes)
    assert summary["status"] == expected
    assert summary["scope"] == "selected_combination"
    verified = construction.load_verified_construction_bundle(tmp_path / "run/construction")
    if expected == "complete":
        portrait = construction.project_hairpin_portrait(
            verified, materialized_realization_id=verified.materialized_realization_ids[0]
        )
        actual = json.loads(portrait.json_bytes)
        assert (
            actual["open_side_paired_positions"],
            actual["loop_side_paired_bp"],
            actual["loop_nt"],
        ) == (17, 6, 4)
    else:
        assert summary["accepted"] == 0
        assert summary["rejection_reasons"] == ["hairpin-scaffold-outside-request"]
        assert summary["scaffold_mismatches"][0]["observed"] == 17
        assert summary["scaffold_mismatches"][0]["required"] == {"minimum": 10, "maximum": 10}
        assert (
            "open_side_paired_positions: requested 10 to 10; observed 17" in execution.report_text
        )
        assert not (tmp_path / "run/handoff").exists()
        assert verified.materialized_realization_ids == ()


@pytest.mark.parametrize(
    "domain",
    [
        {"minimum": 5, "maximum": 3},
        {"minimum": -1, "maximum": 4},
        {"minimum": 3},
        {"minimum": 3, "maximum": 5, "prefer": 4},
    ],
)
def test_invalid_or_ambiguous_scaffold_range_rejects_before_execution(tmp_path, domain):
    path = request_path(tmp_path)
    request = json.loads(path.read_text())
    request["whole_route_constraints"]["hairpin_scaffold"] = {"loop_nt": domain}
    path.write_text(json.dumps(request))
    with pytest.raises(ValueError):
        construction.prepare_construction_request(path)


def test_scaffold_requirements_intersect_but_never_expand_the_authored_search(tmp_path):
    path = request_path(tmp_path)
    request = json.loads(path.read_text())
    request["foldback"]["geometry"]["loop_lengths_nt"] = [3, 4, 5]
    request["whole_route_constraints"]["hairpin_scaffold"] = {
        "loop_nt": {"minimum": 5, "maximum": 5}
    }
    path.write_text(json.dumps(request))
    prepared = construction.prepare_construction_request(path)
    expanded = json.loads(prepared.source_json_bytes)
    assert expanded["foldback"]["geometry_domain"]["loop_lengths_nt"] == [5]
    assert json.loads(prepared.request_json_bytes) == request
    request["whole_route_constraints"]["hairpin_scaffold"]["loop_nt"]["minimum"] = 6
    request["whole_route_constraints"]["hairpin_scaffold"]["loop_nt"]["maximum"] = 6
    path.write_text(json.dumps(request))
    with pytest.raises(ValueError, match="does not intersect"):
        construction.prepare_construction_request(path)
