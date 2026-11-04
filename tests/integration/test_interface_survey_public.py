"""Public survey operations share checkpoint addresses and on-demand handoff."""

import json

from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.unit.test_interface_survey_request import survey_document


def test_cli_api_survey_parity_resume_inspection_and_retrieval(tmp_path):
    document = survey_document()
    document["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    path = tmp_path / "request.json"
    path.write_text(json.dumps(document))
    runner = CliRunner()
    args = [
        "construction",
        "survey",
        "evaluate",
        str(path),
        "--index",
        str(tmp_path / "cli.sqlite"),
        "--max-evaluations",
        "1",
        "--local-nodes",
        "100",
        "--local-realizations",
        "16",
        "--release-site-pairs",
        "100",
    ]
    call = runner.invoke(app, args)
    assert call.exit_code == 0, call.output
    actual = json.loads(call.output)
    expected = construction.evaluate_interface_survey(
        path,
        tmp_path / "api.sqlite",
        max_evaluations=1,
        local_nodes=100,
        local_realizations=16,
        release_site_pairs=100,
    )
    assert actual == expected
    inspected = construction.inspect_interface_survey(path, tmp_path / "api.sqlite")
    assert inspected["evaluations"][0]["left_end"] == "AGTC"
    assert inspected["evaluations"][0]["witnesses"]
    duplicate = runner.invoke(app, args)
    assert duplicate.exit_code != 0
    resumed = runner.invoke(app, [*args, "--resume"])
    assert resumed.exit_code == 0, resumed.output
    assert json.loads(resumed.output)["evaluations"] == 2
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(
        json.dumps(
            construction.load_interface_survey_choices(path, tmp_path / "cli.sqlite").sample(seed=0)
        )
    )
    retrieved = runner.invoke(
        app,
        [
            "construction",
            "survey",
            "retrieve",
            str(path),
            "--index",
            str(tmp_path / "cli.sqlite"),
            "--selection",
            str(selection_path),
            "--out",
            str(tmp_path / "handoff"),
        ],
    )
    assert retrieved.exit_code == 0, retrieved.output
    assert (tmp_path / "handoff/preparation/oligos.csv").is_file()
    verified = construction.verify_interface_survey(path, tmp_path / "api.sqlite")
    assert verified["replayed_evaluations"] == 1
    assert verified["coverage"]["supported_pairs"] == 1
