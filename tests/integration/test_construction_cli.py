"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_construction_cli.py

Tests concise command-line navigation over verified construction authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from rich.text import Text
from typer.testing import CliRunner

from hop_design.cli import app
from hop_design.commands.construction.routes import _route_line
from hop_design.design.construction.complete.bundle import compile_construction_bundle
from hop_design.models.construction import ConstructionEndpoint
from tests.integration.test_complete_construction_projections import _verified_result
from tests.support.claim_language import assert_no_positive_downstream_claims

runner = CliRunner()


@pytest.mark.parametrize(
    ("arguments", "description"),
    (
        (["compile", "--help"], "Compile a payload sequence or a design file."),
        (
            ["construction", "summary", "--help"],
            "Show the endpoint, search coverage, and route counts.",
        ),
        (
            ["construction", "list", "--help"],
            "List routes with explicit filters, grouping, and sorting.",
        ),
        (
            ["construction", "inspect", "--help"],
            "Inspect the materials and molecular steps of one route.",
        ),
        (["construction", "select", "--help"], "Save a selection referencing an existing route."),
    ),
)
def test_command_help_describes_the_user_task(arguments: list[str], description: str) -> None:
    result = runner.invoke(app, arguments, color=False)

    assert result.exit_code == 0, result.output
    assert description in " ".join(result.output.split())


def test_route_line_preserves_zero_basal_overhead() -> None:
    line = _route_line(
        {
            "status": "accepted",
            "ordinal": 0,
            "foldback_retained_overhead_nt": 7,
            "basal_retained_overhead_nt": 0,
            "retained_non_payload_nt": 7,
            "enzyme_ids": (),
            "auxiliary_material_count": 0,
            "materialized_realization_id": "hop:materialized-construction/test@1",
        }
    )

    assert "basal overhead=0 nt" in line


def _write_bundle(
    root: Path,
    *,
    endpoint: ConstructionEndpoint = ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
) -> tuple[Path, object]:
    verified = _verified_result(root / "source", endpoint)
    bundle = compile_construction_bundle(verified).write(root / "construction")
    return bundle, verified


def test_construction_cli_help_exposes_navigation_without_claim_drift() -> None:
    for arguments in (
        ["construction", "--help"],
        ["construction", "summary", "--help"],
        ["construction", "list", "--help"],
        ["construction", "inspect", "--help"],
        ["construction", "select", "--help"],
    ):
        result = runner.invoke(app, arguments)

        assert result.exit_code == 0, result.output
        assert_no_positive_downstream_claims(result.output, surface="construction CLI help")


def test_construction_summary_reports_complete_accounting_and_evidence_boundary(
    tmp_path: Path,
) -> None:
    bundle, verified = _write_bundle(tmp_path)

    result = runner.invoke(app, ["construction", "summary", str(bundle)])

    assert result.exit_code == 0, result.output
    assert f"Result: {verified.result.result_id}" in result.output
    assert "Endpoint: hairpin_pcr_duplex" in result.output
    assert "Search status: complete" in result.output
    assert "Combinations: 2/2 examined" in result.output
    assert "Routes: 2 accepted · 0 rejected · 0 truncated" in result.output
    assert "Geometry groups: 1" in result.output
    assert "Final products: 2" in result.output
    assert "Digital method: resolved under the declared molecular model" in result.output
    assert "Physical construction, QC, and biological activity: not recorded" in result.output
    assert_no_positive_downstream_claims(result.output, surface="construction summary")


def test_construction_list_groups_accepted_routes_and_preserves_canonical_order(
    tmp_path: Path,
) -> None:
    bundle, verified = _write_bundle(tmp_path)
    expected_ids = tuple(item.materialized_realization_id for item in verified.result.realizations)

    result = runner.invoke(
        app,
        [
            "construction",
            "list",
            str(bundle),
            "--group-by",
            "geometry",
            "--sort",
            "canonical",
            "--limit",
            "25",
            "--full-ids",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Query: status=accepted · group_by=geometry · sort=canonical" in result.output
    assert "Foldback:" in result.output
    assert "Basal:" in result.output
    assert "foldback overhead=" in result.output
    assert "basal overhead=" in result.output
    assert "retained non-payload" in result.output
    assert "Ordinal is canonical replay order, not rank." in result.output
    assert result.output.index(expected_ids[0]) < result.output.index(expected_ids[1])
    assert "Showing 2 of 2 matched routes." in result.output


def test_construction_list_leads_with_route_numbers_and_offers_inspection(tmp_path: Path) -> None:
    bundle, verified = _write_bundle(tmp_path)
    result = runner.invoke(app, ["construction", "list", str(bundle), "--descending"])

    assert result.exit_code == 0, result.output
    assert result.output.index("Route 1:") < result.output.index("Route 0:")
    assert "--ordinal NUMBER" in result.output
    assert "--full-ids" in result.output
    for realization in verified.result.realizations:
        assert realization.materialized_realization_id not in result.output


def test_route_number_selection_retains_the_exact_identity(tmp_path: Path) -> None:
    bundle, verified = _write_bundle(tmp_path)
    expected_id = verified.result.realizations[1].materialized_realization_id
    selection = tmp_path / "selected.json"
    selected = runner.invoke(
        app, ["construction", "select", str(bundle), "--ordinal", "1", "--out", str(selection)]
    )
    assert selected.exit_code == 0, selected.output
    assert json.loads(selection.read_text()) == {
        "schema": "hop.construction-selection/v1",
        "source_result_id": verified.result.result_id,
        "materialized_realization_id": expected_id,
    }
    inspected = runner.invoke(app, ["construction", "inspect", str(bundle), "--ordinal", "1"])
    assert inspected.exit_code == 0, inspected.output
    assert f"Realization: {expected_id}" in inspected.output


@pytest.mark.parametrize("ordinal", ["-1", "999"])
def test_unknown_route_number_is_rejected_without_creating_output(
    tmp_path: Path, ordinal: str
) -> None:
    bundle, _ = _write_bundle(tmp_path)
    destination = tmp_path / "selected.json"
    result = runner.invoke(
        app,
        ["construction", "select", str(bundle), "--ordinal", ordinal, "--out", str(destination)],
    )
    assert result.exit_code != 0
    assert "No accepted route has ordinal" in result.output
    assert not destination.exists()


def test_route_number_cannot_be_combined_with_an_exact_identity(tmp_path: Path) -> None:
    bundle, verified = _write_bundle(tmp_path)
    identity = verified.result.realizations[0].materialized_realization_id
    result = runner.invoke(
        app, ["construction", "inspect", str(bundle), identity, "--ordinal", "0"]
    )
    assert result.exit_code != 0
    assert "Provide exactly one" in result.output


def test_construction_list_filters_and_sorts_only_on_explicit_dimensions(
    tmp_path: Path,
) -> None:
    bundle, verified = _write_bundle(tmp_path)
    enzyme_id = next(
        operation.enzyme_id
        for program in verified.result.realizations[0].construction_program.reaction_programs
        for stage in program.stages
        for operation in stage.operations
    )

    unknown_group = runner.invoke(
        app,
        ["construction", "list", str(bundle), "--group", "hop:geometry/unknown@1"],
    )
    explicit_sort = runner.invoke(
        app,
        [
            "construction",
            "list",
            str(bundle),
            "--sort",
            "retained-overhead",
            "--descending",
        ],
    )
    enzyme_match = runner.invoke(
        app,
        ["construction", "list", str(bundle), "--enzyme", enzyme_id],
    )
    unknown_enzyme = runner.invoke(
        app,
        ["construction", "list", str(bundle), "--enzyme", "hop:enzyme/not-present@1"],
    )
    rejected_enzyme = runner.invoke(
        app,
        [
            "construction",
            "list",
            str(bundle),
            "--status",
            "rejected",
            "--group-by",
            "none",
            "--enzyme",
            enzyme_id,
        ],
    )
    mixed_enzyme = runner.invoke(
        app,
        [
            "construction",
            "list",
            str(bundle),
            "--status",
            "all",
            "--group-by",
            "none",
            "--enzyme",
            enzyme_id,
        ],
    )
    limited = runner.invoke(
        app,
        ["construction", "list", str(bundle), "--limit", "1"],
    )

    assert unknown_group.exit_code != 0
    assert "Unknown achieved-geometry group" in unknown_group.output
    assert explicit_sort.exit_code == 0, explicit_sort.output
    assert "sort=retained-overhead · order=descending" in explicit_sort.output
    assert "rank" not in explicit_sort.output.lower().replace("not rank", "")
    assert enzyme_match.exit_code == 0, enzyme_match.output
    assert "Showing 2 of 2 matched routes." in enzyme_match.output
    assert unknown_enzyme.exit_code != 0
    assert "Unknown route enzyme" in unknown_enzyme.output
    assert rejected_enzyme.exit_code != 0
    assert "Enzyme filters apply only to accepted routes" in rejected_enzyme.output
    assert mixed_enzyme.exit_code != 0
    assert "Enzyme filters apply only to accepted routes" in mixed_enzyme.output
    assert limited.exit_code == 0, limited.output
    assert "Showing 1 of 2 matched routes." in limited.output
    assert "Display limiting does not change the verified search status" in limited.output


def test_construction_inspect_prints_one_exact_route_and_exports_create_only(
    tmp_path: Path,
) -> None:
    bundle, verified = _write_bundle(tmp_path)
    realization_id = verified.result.realizations[0].materialized_realization_id
    output = tmp_path / "trajectory"

    result = runner.invoke(
        app,
        [
            "construction",
            "inspect",
            str(bundle),
            realization_id,
            "--out",
            str(output),
            "--reason",
            "Uses the required enzymes and endpoint.",
        ],
    )

    assert result.exit_code == 0, result.output
    assert f"Realization: {realization_id}" in result.output
    assert "Source ssDNA:" in result.output
    assert "Required external materials:" in result.output
    assert "Molecular states:" in result.output
    assert "Endpoint: hairpin_pcr_duplex · linear_duplex" in result.output
    assert "Physical construction, QC, and biological activity: not recorded" in result.output
    assert {item.name for item in output.iterdir()} == {
        "projection.json",
        "projection.svg",
        "report.md",
        "oligos.csv",
        "oligos.fasta",
    }
    assert "Uses the required enzymes and endpoint." in (output / "report.md").read_text()

    repeated = runner.invoke(
        app,
        [
            "construction",
            "inspect",
            str(bundle),
            realization_id,
            "--out",
            str(output),
        ],
    )
    assert repeated.exit_code != 0
    assert "Refusing to replace existing" in repeated.output
    assert "projection path" in repeated.output


@pytest.mark.parametrize("color", [False, True])
def test_inspection_reason_requires_saved_output(tmp_path: Path, color: bool) -> None:
    bundle, _ = _write_bundle(tmp_path)
    result = runner.invoke(
        app,
        ["construction", "inspect", str(bundle), "--ordinal", "0", "--reason", "My choice"],
        color=color,
    )
    assert result.exit_code != 0
    assert "--reason requires --out" in Text.from_ansi(result.output).plain


def test_construction_selection_is_result_bound_and_reusable_for_inspection(
    tmp_path: Path,
) -> None:
    first_bundle, first = _write_bundle(tmp_path / "first")
    second_bundle, _ = _write_bundle(
        tmp_path / "second",
        endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
    )
    realization_id = first.result.realizations[0].materialized_realization_id
    selection_path = tmp_path / "selected.json"

    selected = runner.invoke(
        app,
        [
            "construction",
            "select",
            str(first_bundle),
            realization_id,
            "--out",
            str(selection_path),
        ],
    )

    assert selected.exit_code == 0, selected.output
    content = json.loads(selection_path.read_text(encoding="utf-8"))
    assert content == {
        "schema": "hop.construction-selection/v1",
        "source_result_id": first.result.result_id,
        "materialized_realization_id": realization_id,
    }

    inspected = runner.invoke(
        app,
        [
            "construction",
            "inspect",
            str(first_bundle),
            "--selection",
            str(selection_path),
        ],
    )
    mismatched = runner.invoke(
        app,
        [
            "construction",
            "inspect",
            str(second_bundle),
            "--selection",
            str(selection_path),
        ],
    )

    assert inspected.exit_code == 0, inspected.output
    assert f"Realization: {realization_id}" in inspected.output
    assert mismatched.exit_code != 0
    assert "Construction selection does not belong to" in mismatched.output
    assert "this verified construction result" in mismatched.output


def test_construction_exports_cannot_modify_their_verified_input_bundle(tmp_path: Path) -> None:
    bundle, verified = _write_bundle(tmp_path)
    realization_id = verified.result.realizations[0].materialized_realization_id

    selected = runner.invoke(
        app,
        [
            "construction",
            "select",
            str(bundle),
            realization_id,
            "--out",
            str(bundle / "selected.json"),
        ],
    )
    inspected = runner.invoke(
        app,
        [
            "construction",
            "inspect",
            str(bundle),
            realization_id,
            "--out",
            str(bundle / "trajectory"),
        ],
    )

    assert selected.exit_code != 0
    assert "must be outside the verified construction" in selected.output
    assert "bundle." in selected.output
    assert inspected.exit_code != 0
    assert "must be outside the verified construction" in inspected.output
    assert "bundle." in inspected.output
    assert not (bundle / "selected.json").exists()
    assert not (bundle / "trajectory").exists()

    replay = runner.invoke(app, ["construction", "summary", str(bundle)])
    assert replay.exit_code == 0, replay.output
