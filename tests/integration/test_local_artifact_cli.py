from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.design.construction.execution import local as execution

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


def test_oversized_batch_report_preserves_complete_checkpoint_and_stops_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = ROOT / "examples/foldback-local-partition.yaml"
    local = construction.discover_local_neighborhood(source)
    individual = local.write(tmp_path / "individual") / "result.json"
    runner = CliRunner()
    expected = runner.invoke(app, ["construction", "verify-local", str(individual)])
    assert expected.exit_code == 0, expected.output
    report_limit = len(expected.stdout.encode("utf-8")) + 1024
    monkeypatch.setattr(execution, "_REPORT_MAX_BYTES", report_limit, raising=False)
    replayed: list[str] = []
    original_iter = construction.LocalNeighborhoodBatch.iter_results

    def observe_replay(self: construction.LocalNeighborhoodBatch):
        for result in original_iter(self):
            replayed.append(result.result_id)
            yield result

    monkeypatch.setattr(construction.LocalNeighborhoodBatch, "iter_results", observe_replay)
    checkpoint = tmp_path / "checkpoint"
    arguments = [
        "construction",
        "discover-batch",
        *([str(source)] * 3),
        "--checkpoint",
        str(checkpoint),
    ]
    initial = runner.invoke(app, arguments)
    assert initial.exit_code != 0
    assert initial.stdout == ""
    assert "aggregate report" in " ".join(initial.output.split())
    assert "iter_results()" in initial.output
    assert len(replayed) == 2
    before = {
        path.relative_to(checkpoint): path.read_bytes()
        for path in checkpoint.rglob("*")
        if path.is_file()
    }
    assert Path("complete.json") in before
    replayed.clear()
    resumed = runner.invoke(app, [*arguments, "--resume"])
    assert resumed.exit_code != 0
    assert resumed.stdout == ""
    assert "aggregate report" in " ".join(resumed.output.split())
    assert len(replayed) == 2
    assert {
        path.relative_to(checkpoint): path.read_bytes()
        for path in checkpoint.rglob("*")
        if path.is_file()
    } == before
    batch = construction.discover_local_neighborhoods([source] * 3, checkpoint, resume=True)
    assert batch.finished and batch.completed_requests == 3
    assert [result.json_bytes for result in batch.iter_results()] == [local.json_bytes] * 3
    verified = runner.invoke(app, ["construction", "verify-local", str(individual)])
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.stdout) == json.loads(expected.stdout)
    monkeypatch.setattr(execution, "_REPORT_MAX_BYTES", 64 * 1024 * 1024)
    recovered = runner.invoke(app, [*arguments, "--resume"])
    assert recovered.exit_code == 0, recovered.output
    assert json.loads(recovered.stdout) == {
        "schema": "hop/local-batch-report/v1",
        "finished": True,
        "planned_requests": 3,
        "completed_requests": 3,
        "results": [json.loads(expected.stdout)] * 3,
    }


def test_batch_report_counts_envelope_separators_and_stdout_newline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = ROOT / "examples/foldback-local-partition.yaml"
    batch = construction.discover_local_neighborhoods([source] * 3, tmp_path / "checkpoint")
    expected = json.dumps(
        {
            "schema": "hop/local-batch-report/v1",
            "finished": True,
            "planned_requests": 3,
            "completed_requests": 3,
            "results": [json.loads(result.report_json()) for result in batch.iter_results()],
        },
        sort_keys=True,
    )
    exact_size = len(expected.encode("utf-8")) + 1
    monkeypatch.setattr(execution, "_REPORT_MAX_BYTES", exact_size)
    assert batch.report_json() == expected
    monkeypatch.setattr(execution, "_REPORT_MAX_BYTES", exact_size - 1)
    with pytest.raises(ValueError, match="aggregate report"):
        batch.report_json()
    first_only = json.loads(expected)
    first_only["results"] = first_only["results"][:1]
    first_size = len(json.dumps(first_only, sort_keys=True).encode("utf-8")) + 1
    monkeypatch.setattr(execution, "_REPORT_MAX_BYTES", first_size)
    replayed = []
    original_iter = construction.LocalNeighborhoodBatch.iter_results

    def observe_replay(self: construction.LocalNeighborhoodBatch):
        for result in original_iter(self):
            replayed.append(result.result_id)
            yield result

    monkeypatch.setattr(construction.LocalNeighborhoodBatch, "iter_results", observe_replay)
    with pytest.raises(ValueError, match="aggregate report"):
        batch.report_json()
    assert len(replayed) == 1
    replayed.clear()
    monkeypatch.setattr(execution, "_REPORT_MAX_BYTES", 1)
    with pytest.raises(ValueError, match="aggregate report"):
        batch.report_json()
    assert replayed == []


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
