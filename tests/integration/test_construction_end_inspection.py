"""Inspect oriented end origins through the public construction receipt and CLI."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.design.construction.complete.bundle import compile_construction_bundle
from hop_design.models.construction import ConstructionEndpoint
from tests.integration.test_complete_construction_projections import _verified_result


@pytest.fixture
def selected(tmp_path):
    verified = _verified_result(tmp_path / "source", ConstructionEndpoint.CLONE_READY_DUPLEX)
    bundle = compile_construction_bundle(verified).write(tmp_path / "bundle")
    receipt = construction.load_verified_construction_bundle(bundle)
    projection = construction.project_construction_trajectory(
        receipt, materialized_realization_id=receipt.materialized_realization_ids[0]
    )
    return bundle, receipt, projection


def test_end_inspection_preserves_roles_for_identical_primer_sequences(selected) -> None:
    bundle, receipt, projection = selected
    before = projection.json_bytes
    for side, role, cuts in (
        ("left", "endpoint_forward_primer", "primary=6; complementary=10"),
        ("right", "endpoint_reverse_primer", "primary=29; complementary=33"),
    ):
        explained = projection.inspect_end(side)
        assert f"{side.capitalize()} cohesive end: AAAA (5-prime to 3-prime)" in explained
        assert (
            "Indexes: zero-based; end and material indexes follow "
            "their own 5-prime to 3-prime sequences" in explained
        )
        assert cuts in explained
        for index in range(4):
            assert f"end[{index}] A <- {role}[{index + 6}] A" in explained
        assert receipt.result_id in explained
        assert projection.source_result_id in explained
        inspected = CliRunner().invoke(
            app, ["construction", "inspect", str(bundle), "--ordinal", "0", "--end", side]
        )
        assert inspected.exit_code == 0, inspected.output
        assert inspected.output == explained + "\n"
    assert projection.json_bytes == before


def test_end_base_selection_is_relative_to_its_oriented_word(selected) -> None:
    bundle, _, projection = selected
    text = projection.inspect_end("right", base_index=2)
    assert "end[2] A <- endpoint_reverse_primer[8] A" in text
    assert "end[0]" not in text
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "inspect",
            str(bundle),
            "--ordinal",
            "0",
            "--end",
            "right",
            "--base-index",
            "2",
        ],
    )
    assert result.exit_code == 0, result.output
    assert result.output == text + "\n"


@pytest.mark.parametrize(
    "side,index",
    [("top", None), ("LEFT", None), ("left", -1), ("right", 4), ("left", True), ("left", 1.0)],
)
def test_end_inspection_rejects_invalid_selection(selected, side, index) -> None:
    with pytest.raises(ValueError):
        selected[2].inspect_end(side, base_index=index)


@pytest.mark.parametrize(
    "options", [["--base-index", "0"], ["--end", "top"], ["--end", "left", "--base-index", "4"]]
)
def test_invalid_end_focus_does_not_write_handoff(selected, tmp_path: Path, options) -> None:
    destination = tmp_path / "handoff"
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "inspect",
            str(selected[0]),
            "--ordinal",
            "0",
            "--out",
            str(destination),
            *options,
        ],
    )
    assert result.exit_code != 0
    assert not destination.exists()


def test_end_inspection_requires_a_released_selected_product(selected, tmp_path: Path) -> None:
    summary = construction.project_complete_construction_summary(selected[1])
    with pytest.raises(ValueError, match="selected trajectory"):
        summary.inspect_end("left")
    verified = _verified_result(tmp_path / "pcr", ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    bundle = compile_construction_bundle(verified).write(tmp_path / "pcr-bundle")
    receipt = construction.load_verified_construction_bundle(bundle)
    projection = construction.project_construction_trajectory(
        receipt, materialized_realization_id=receipt.materialized_realization_ids[0]
    )
    with pytest.raises(ValueError, match="released"):
        projection.inspect_end("left")
