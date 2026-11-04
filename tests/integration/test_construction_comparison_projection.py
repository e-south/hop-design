"""A comparison exposes real regional changes without treating moved bases as mutations."""

import json

import pytest

from hop_design import construction
from tests.integration.test_request_execution import request_path


@pytest.fixture(scope="module")
def loop_series(tmp_path_factory):
    root = tmp_path_factory.mktemp("comparison-series")
    receipts = []
    for loop in (3, 4):
        directory = root / str(loop)
        directory.mkdir()
        path = request_path(directory)
        request = json.loads(path.read_text())
        request["foldback"]["geometry"]["annealing_arm_lengths_bp"] = [7]
        request["foldback"]["geometry"]["loop_lengths_nt"] = [loop]
        request["foldback"]["search"]["max_retained_overhead_nt"] = 21
        path.write_text(json.dumps(request))
        execution = construction.execute_construction_request(
            path, design_id=f"loop-{loop}", continuation="sole-witness"
        )
        execution.write(directory / "execution")
        receipts.append(
            construction.load_verified_construction_bundle(directory / "execution/construction")
        )
    return receipts, root


def test_comparison_projection_distinguishes_loop_edit_from_coordinate_shift(loop_series):
    left, right = loop_series[0]
    comparison = construction.project_construction_comparison(
        left,
        right,
        left_realization_id=left.materialized_realization_ids[0],
        right_realization_id=right.materialized_realization_ids[0],
    )
    data = json.loads(comparison.json_bytes)
    assert data["schema"] == "hop.construction-comparison/v2"
    assert data["left"]["source_result_id"] == left.result_id
    assert data["right"]["source_result_id"] == right.result_id
    properties = {p["field"]: p for p in data["properties"]}
    assert properties["hairpin.loop_nt"]["left"] == 3
    assert properties["hairpin.loop_nt"]["right"] == 4
    assert properties["hairpin.loop_side_paired_bp"]["changed"] is False
    assert properties["hairpin.region.stem_return.sequence"]["changed"] is False
    assert properties["hairpin.region.stem_return.span"]["changed"] is True
    assert properties["hairpin.region.loop.sequence"]["changed"] is True
    assert data["changed_material_roles"] == [
        "source_ssdna",
        "source_materialization_reverse_primer",
    ]
    assert comparison.report_text == construction.compare_constructions(
        left,
        right,
        left_realization_id=left.materialized_realization_ids[0],
        right_realization_id=right.materialized_realization_ids[0],
    )


def test_comparison_rejects_unknown_member(loop_series):
    left, right = loop_series[0]
    with pytest.raises(ValueError, match="Unknown accepted"):
        construction.project_construction_comparison(
            left,
            right,
            left_realization_id="unknown",
            right_realization_id=right.materialized_realization_ids[0],
        )


def test_comparison_cli_exports_the_same_structured_facts(loop_series):
    from typer.testing import CliRunner

    from hop_design.cli import app

    (left, right), root = loop_series
    output = CliRunner().invoke(
        app,
        [
            "construction",
            "compare",
            str(root / "3/execution/construction"),
            str(root / "4/execution/construction"),
            "--left-ordinal",
            "0",
            "--right-ordinal",
            "0",
            "--format",
            "json",
        ],
    )
    assert output.exit_code == 0, output.output
    expected = construction.project_construction_comparison(
        left,
        right,
        left_realization_id=left.materialized_realization_ids[0],
        right_realization_id=right.materialized_realization_ids[0],
    )
    assert output.output.encode() == expected.json_bytes
