"""
--------------------------------------------------------------------------------
HOP Design
hop-design/tests/integration/test_selection_admission.py

Check selection input errors before public exports or material retrieval.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import copy
import json

import pytest
from typer.testing import CliRunner

from hop_design.cli import app
from tests.integration.test_atlas_edition import captured_choices, captured_edition  # noqa: F401


@pytest.mark.parametrize("operation", ["figure", "view", "atlas", "retrieve"])
@pytest.mark.parametrize(
    "source,message",
    [
        ([], "Selection must be a JSON object"),
        (False, "Selection must be a JSON object"),
        (0, "Selection must be a JSON object"),
        ({0: "unexpected"}, "Selection keys must be strings"),
        ({0: "unexpected", "schema": "unknown"}, "Selection keys must be strings"),
        ({"schema": None}, "Selection schema must be a string"),
        ({"schema": []}, "Selection schema must be a string"),
        ({"schema": {}}, "Selection schema must be a string"),
        ({"schema": False}, "Selection schema must be a string"),
    ],
)
def test_malformed_selection_fails_before_public_output(
    captured_edition,  # noqa: F811
    tmp_path,
    operation,
    source,
    message,
):
    before = copy.deepcopy(source)
    output = tmp_path / "export"
    with pytest.raises(ValueError, match=message):
        if operation == "retrieve":
            captured_edition.retrieve(source, output)
        elif operation == "view":
            captured_edition.view(source)
        else:
            getattr(captured_edition, operation)(selection=source).write(output)
    assert source == before
    assert not output.exists()


def test_malformed_selection_file_has_a_readable_cli_error(captured_edition, tmp_path):  # noqa: F811
    source = tmp_path / "selection.json"
    source.write_text(json.dumps({"schema": None}))
    output = tmp_path / "materials"
    result = CliRunner().invoke(
        app,
        [
            "design",
            "retrieve",
            str(captured_edition._directory),
            "--selection",
            str(source),
            "--out",
            str(output),
        ],
    )
    assert result.exit_code != 0
    assert "Selection schema must be a string" in result.output
    assert not output.exists()


def test_figure_can_omit_selection(captured_edition):  # noqa: F811
    summary = json.loads(captured_edition.figure(selection=None).json_bytes)
    assert summary.get("selection") is None
