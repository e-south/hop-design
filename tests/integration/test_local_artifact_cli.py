from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app

ROOT = Path(__file__).resolve().parents[2]


def test_local_discovery_report_roundtrips_public_authority(tmp_path: Path) -> None:
    source = ROOT / "examples/foldback-local-partition.yaml"
    expected = construction.discover_local_neighborhood(source)
    output = tmp_path / "local"
    runner = CliRunner()

    result = runner.invoke(
        app, ["construction", "discover-local", str(source), "--out", str(output)]
    )

    assert result.exit_code == 0, result.output
    assert (output / "result.json").read_bytes() == expected.json_bytes
    report = json.loads(result.output)
    assert report["result_id"] == expected.result_id
    assert report["completion"] == expected.completion
    verified = runner.invoke(app, ["construction", "verify-local", str(output / "result.json")])
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.output) == report


def test_local_projection_cli_preserves_public_packet_bytes(tmp_path: Path) -> None:
    source = ROOT / "examples/foldback-local-partition.yaml"
    receipt = construction.discover_local_neighborhood(source)
    result_path = tmp_path / "result.json"
    result_path.write_bytes(receipt.json_bytes)
    expected = construction.project_foldback_feasibility(receipt)
    output = tmp_path / "projection"

    result = CliRunner().invoke(
        app,
        [
            "construction",
            "project",
            str(result_path),
            "--kind",
            "foldback-feasibility",
            "--out",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (output / "projection.json").read_bytes() == expected.json_bytes
    assert (output / "projection.csv").read_bytes() == expected.csv_bytes
    assert (output / "projection.svg").read_bytes() == expected.svg_bytes


def test_local_batch_preserves_request_order_and_resume(tmp_path: Path) -> None:
    source = ROOT / "examples/foldback-local-partition.yaml"
    runner = CliRunner()
    arguments = [
        "construction",
        "discover-batch",
        str(source),
        "--checkpoint",
        str(tmp_path / "checkpoint"),
    ]
    initial = runner.invoke(app, arguments)
    assert initial.exit_code == 0, initial.output
    report = json.loads(initial.output)
    assert report["finished"] is True
    assert report["planned_requests"] == report["completed_requests"] == 1
    assert len(report["results"]) == 1
    resumed = runner.invoke(app, [*arguments, "--resume"])
    assert resumed.exit_code == 0, resumed.output
    assert json.loads(resumed.output) == report


def test_basal_choices_panels_and_projection_files_match_owner(tmp_path: Path) -> None:
    receipt = construction.discover_local_neighborhood(
        ROOT / "examples/basal-junction/request.yaml"
    )
    source = tmp_path / "result.json"
    source.write_bytes(receipt.json_bytes)
    runner = CliRunner()
    inspected = runner.invoke(
        app, ["construction", "local-choices", str(source), "--sort-by", "retained_overhead_nt"]
    )
    assert inspected.exit_code == 0, inspected.output
    rows = json.loads(inspected.output)["choices"]
    expected = construction.list_local_realizations(receipt, sort_by=("retained_overhead_nt",))
    assert [row["realization_id"] for row in rows] == [row.realization_id for row in expected]
    selected = json.loads(receipt.json_bytes)["realizations"][0]["local_realization"][
        "local_realization_id"
    ]
    panel = runner.invoke(
        app, ["construction", "basal-panel", str(source), "--realization-id", selected]
    )
    assert panel.exit_code == 0, panel.output
    assert json.loads(panel.output)["panel"] == json.loads(
        construction.project_basal_source_panel(receipt, realization_id=selected)
    )
    kinds = {
        "basal-feasibility": construction.project_basal_feasibility(receipt),
        "basal-minimum-overhead": construction.project_basal_minimum_overhead_matrix(receipt),
        "basal-retained-overhead": construction.project_retained_overhead_frontier(
            receipt, family="basal"
        ),
    }
    for kind, projection in kinds.items():
        output = tmp_path / kind
        result = runner.invoke(
            app, ["construction", "project", str(source), "--kind", kind, "--out", str(output)]
        )
        assert result.exit_code == 0, result.output
        assert (output / "projection.json").read_bytes() == projection.json_bytes
        assert (output / "projection.svg").read_bytes() == projection.svg_bytes


@pytest.mark.parametrize(
    "command",
    [
        "discover-local",
        "verify-local",
        "discover-partition",
        "verify-partition",
        "local-choices",
        "basal-panel",
    ],
)
def test_invalid_local_file_never_emits_a_success_report(tmp_path: Path, command: str) -> None:
    source = tmp_path / "invalid.json"
    source.write_text("{}")
    arguments = ["construction", command, str(source)]
    if command.startswith("discover"):
        arguments += ["--out", str(tmp_path / "output")]
    if command == "basal-panel":
        arguments += ["--realization-id", "invalid"]
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code != 0
    assert '"verification"' not in result.output
    assert not (tmp_path / "output").exists()
