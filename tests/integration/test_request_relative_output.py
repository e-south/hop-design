"""Everyday relative destinations preserve create-only request handoffs."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design.cli import app

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("command", ["prepare", "execute"])
def test_relative_parent_output_is_published_and_not_replaced(tmp_path, monkeypatch, command):
    working = tmp_path / "working"
    working.mkdir()
    monkeypatch.chdir(working)
    args = [
        "construction",
        command,
        str(ROOT / "examples/complete-construction/product-request.json"),
        "--out",
        "../outcome",
    ]
    if command == "execute":
        args += ["--design-id", "relative-output", "--continuation", "sole-witness"]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    expected = "preview.json" if command == "prepare" else "summary.json"
    retained = (tmp_path / "outcome" / expected).read_bytes()
    repeated = CliRunner().invoke(app, args)
    assert repeated.exit_code == 2
    assert (tmp_path / "outcome" / expected).read_bytes() == retained
