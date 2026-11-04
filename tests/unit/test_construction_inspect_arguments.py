"""Reject intent errors before loading a potentially expensive authority."""

import pytest
from rich.text import Text
from typer.testing import CliRunner

from hop_design.cli import app
from hop_design.commands.construction import selection


@pytest.mark.parametrize("force_color", ["0", "1"])
@pytest.mark.parametrize(
    "options,message",
    [
        (["--ordinal", "0", "--end", "top"], "--end must be left or right"),
        (["--ordinal", "0", "--end", "left", "--base-index", "-1"], "nonnegative"),
        (["--ordinal", "-1"], "nonnegative"),
        ([], "exactly one route selector"),
        (["an-id", "--ordinal", "0"], "exactly one route selector"),
    ],
)
def test_invalid_inspection_arguments_do_not_load_bundle(
    monkeypatch, options, message, force_color
):
    def unexpected_load(*args, **kwargs):
        pytest.fail("Independent argument validation must precede replay")

    monkeypatch.setattr(selection, "load_receipt", unexpected_load)
    monkeypatch.setenv("FORCE_COLOR", force_color)
    result = CliRunner().invoke(app, ["construction", "inspect", "missing-bundle", *options])
    assert result.exit_code == 2, result.output
    assert message in " ".join(Text.from_ansi(result.output).plain.split())
