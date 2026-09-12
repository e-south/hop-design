"""Named method commands preserve the existing request, outcome, and bundle formats."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design.cli import app
from tests.support.linear_source_method import linear_source_method_request


@pytest.mark.parametrize("command", ["resolve-linear-source", "compile-linear-source"])
def test_method_commands_reject_ambiguous_request_keys(tmp_path: Path, command: str) -> None:
    encoded = linear_source_method_request().model_dump_json(by_alias=True)
    source = tmp_path / "request.json"
    source.write_text('{"request_id":"first-intent",' + encoded[1:])
    output = tmp_path / "bundle"
    arguments = ["method", command, str(source)]
    if command == "compile-linear-source":
        arguments += ["--out", str(output)]
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code != 0
    assert "duplicate mapping key" in " ".join(result.output.split())
    assert not output.exists()


def test_method_file_commands_keep_the_json_input_contract(tmp_path: Path) -> None:
    source = tmp_path / "request.yaml"
    source.write_text(linear_source_method_request().model_dump_json(by_alias=True))
    result = CliRunner().invoke(app, ["method", "resolve-linear-source", str(source)])
    assert result.exit_code != 0
    assert ".json" in result.output


def test_method_commands_resolve_compile_and_verify_exact_authorities(tmp_path: Path) -> None:
    request = linear_source_method_request()
    source = tmp_path / "request.json"
    source.write_text(request.model_dump_json(by_alias=True))
    runner = CliRunner()
    resolved = runner.invoke(app, ["method", "resolve-linear-source", str(source)])
    assert resolved.exit_code == 0, resolved.output
    result = json.loads(resolved.output)
    assert result["result"]["outcome"]["resolution_status"] == "complete"
    output = tmp_path / "bundle"
    compiled = runner.invoke(
        app, ["method", "compile-linear-source", str(source), "--out", str(output)]
    )
    assert compiled.exit_code == 0, compiled.output
    report = json.loads(compiled.output)
    assert report["result"] == result["result"]
    assert report["result"]["plan"] == json.loads((output / "method-plan.json").read_bytes())
    assert report["bundle"] == json.loads((output / "method-bundle.json").read_bytes())
    verified = runner.invoke(app, ["method", "verify-linear-source", str(output)])
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.output) == report
    (output / "method-plan.json").write_bytes(b"{}")
    assert runner.invoke(app, ["method", "verify-linear-source", str(output)]).exit_code != 0


def test_method_resolution_preserves_expected_infeasibility_without_publication(
    tmp_path: Path,
) -> None:
    source = tmp_path / "request.json"
    source.write_text(linear_source_method_request(min_length_nt=70).model_dump_json(by_alias=True))
    runner = CliRunner()
    result = runner.invoke(app, ["method", "resolve-linear-source", str(source)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["result"]["plan"] is None
    assert report["result"]["outcome"]["resolution_status"] == "infeasible"
    output = tmp_path / "bundle"
    assert (
        runner.invoke(
            app, ["method", "compile-linear-source", str(source), "--out", str(output)]
        ).exit_code
        != 0
    )
    assert not output.exists()
