"""A permitted program is distinct from a local pair actually sent to compilation."""

import json

import pytest

from hop_design import construction
from hop_design.design.construction.surveys import admission
from tests.integration.test_survey_admission_batching import request_path


def test_inspection_reports_attempted_pair_without_discovery_or_replay(tmp_path, monkeypatch):
    path = request_path(tmp_path)
    index = tmp_path / "index.sqlite"
    construction.evaluate_interface_survey(
        path,
        index,
        max_evaluations=2,
        local_nodes=100,
        local_realizations=16,
        release_site_pairs=100,
    )
    before = index.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("Inspection must not discover or replay molecules.")

    monkeypatch.setattr(admission.locals, "_discover_request", forbidden)
    monkeypatch.setattr(admission.locals, "_verify_result_mapping", forbidden)
    report = construction.inspect_interface_survey(path, index)
    empty, attempted = report["evaluations"]
    assert empty["evaluated_local_pair"] is None
    pair = attempted["evaluated_local_pair"]
    assert pair is not None
    assert pair["foldback"]["nick_enzyme_id"] == "example:enzyme/nt.bpu10i@1"
    assert pair["basal"]["nick_enzyme_id"] == "example:enzyme/nb.bsrdi@1"
    assert pair["foldback"]["geometry"]["loop_length_nt"] == 4
    assert pair["basal"]["geometry"]["future_release"]["payload_end_offset_bp"] == 6
    assert attempted["witnesses"]
    assert index.read_bytes() == before

    from typer.testing import CliRunner

    from hop_design.commands.construction.survey import survey_app

    result = CliRunner().invoke(survey_app, ["inspect", str(path), "--index", str(index)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == report


@pytest.mark.parametrize("failure", ["missing", "result", "pair"])
def test_inspection_rejects_missing_or_mismatched_local_evidence(tmp_path, monkeypatch, failure):
    from hop_design.design.construction.surveys.execute import load_request
    from hop_design.design.construction.surveys.index import SurveyIndex
    from hop_design.design.construction.surveys.inspection import evaluated_local_pair
    from hop_design.design.runtime import producer_identity

    path = request_path(tmp_path)
    checkpoint = tmp_path / "index.sqlite"
    construction.evaluate_interface_survey(
        path,
        checkpoint,
        max_evaluations=2,
        local_nodes=100,
        local_realizations=16,
        release_site_pairs=100,
    )
    index, _ = admission.open_survey(
        checkpoint, request=load_request(path), producer=producer_identity()
    )
    with index:
        record = json.loads(list(index.evaluations())[1][2])
        if failure == "missing":
            monkeypatch.setattr(SurveyIndex, "cached", lambda *args: None)
        elif failure == "result":
            record["local_coverage"]["foldback"]["result_id"] = "wrong"
        else:
            record["pair"] = record["recorded_pairs"]
        with pytest.raises(ValueError, match="local pair"):
            evaluated_local_pair(index, record)


def test_context_completion_inspection_separates_navigation_from_compilation(tmp_path):
    from tests.support.context_completion import LIMITS, request

    path = request(tmp_path, "completion", completion=True)
    index = tmp_path / "index.sqlite"
    construction.evaluate_interface_survey(path, index, max_evaluations=4, **LIMITS)
    rows = construction.inspect_interface_survey(path, index)["evaluations"]
    assert any(row["evaluated_local_pair"] is None for row in rows)
    assert any(row["evaluated_local_pair"] is not None for row in rows)
    assert all(row["evaluated_local_pair"] is not None for row in rows if row["witnesses"])
