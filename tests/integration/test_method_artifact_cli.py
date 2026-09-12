"""Named method commands preserve the existing request, outcome, and bundle formats."""

import json
from pathlib import Path

from typer.testing import CliRunner

from hop_design.cli import app
from tests.support.linear_source_method import linear_source_method_request


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
