"""Empty admissions can be batched without changing the next complete candidate."""

import json

import pytest

from hop_design.design.construction.surveys.execute import evaluate_interface_survey, load_request
from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.design.construction.surveys.verify import verify_interface_survey
from hop_design.design.runtime import producer_identity
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from tests.unit.test_interface_survey_request import survey_document


def request_path(tmp_path):
    document = survey_document()
    document["targets"] = {"left_words": ["AAAA"], "right_words": ["AAAA"]}
    document["basal"]["annealing_lengths_nt"] = [17]
    path = tmp_path / "survey.json"
    path.write_text(json.dumps(document))
    return path


def limits(batch=1):
    return SurveyEvaluationLimits(
        local_nodes=100,
        local_realizations=16,
        release_site_pairs=100,
        continuation_batch_size=batch,
    )


def records(path, index_path, budget):
    with SurveyIndex.open(
        index_path,
        request=load_request(path),
        producer=producer_identity(),
        limits=budget.model_dump(mode="json"),
    ) as index:
        return [json.loads(raw) for _, _, raw, _, _ in index.evaluations()]


def test_batch_reaches_same_witness_and_retains_empty_admission(tmp_path):
    path = request_path(tmp_path)
    a = evaluate_interface_survey(
        path, tmp_path / "single.sqlite", limits=limits(), max_evaluations=2
    )
    b = evaluate_interface_survey(
        path, tmp_path / "batch.sqlite", limits=limits(4), max_evaluations=1
    )
    assert a["coverage"] == b["coverage"]
    assert b["coverage"]["supported_pairs"] == 1
    assert a["continuations_examined"] == b["continuations_examined"] == 2
    assert b["new_continuations_examined"] == 2
    single = records(path, tmp_path / "single.sqlite", limits())
    batched = records(path, tmp_path / "batch.sqlite", limits(4))[0]
    assert len(single) == 2
    assert len(batched["skipped_empty"]) == 1
    skipped = batched["skipped_empty"][0]
    for key in (
        "branch",
        "page",
        "pair",
        "local_coverage",
        "rejection",
        "next",
        "exhaustion_proven",
    ):
        assert skipped[key] == single[0][key]
    for key in ("branch", "page", "pair", "witnesses", "product_request", "bundle", "next"):
        assert batched[key] == single[1][key]
    assert verify_interface_survey(path, tmp_path / "batch.sqlite")["coverage"] == b["coverage"]


def test_batch_limit_preserves_pending_cursor_and_resumed_records(tmp_path):
    path = request_path(tmp_path)
    document = json.loads(path.read_text())
    document["foldback"]["geometry"]["junction_offsets_nt"] = [0]
    document["placements"] = [{"left_bp": gap, "right_bp": gap} for gap in (0, 1, 2, 6)]
    path.write_text(json.dumps(document))
    budget = limits(2)
    first = evaluate_interface_survey(
        path, tmp_path / "split.sqlite", limits=budget, max_evaluations=1
    )
    assert first["coverage"]["excluded_pairs"] == 0
    assert first["coverage"]["unresolved_pairs"] == 1
    resumed = evaluate_interface_survey(
        path, tmp_path / "split.sqlite", limits=budget, max_evaluations=2, resume=True
    )
    whole = evaluate_interface_survey(
        path, tmp_path / "whole.sqlite", limits=budget, max_evaluations=3
    )
    assert resumed["coverage"] == whole["coverage"]
    assert resumed["continuations_examined"] == whole["continuations_examined"]
    assert records(path, tmp_path / "split.sqlite", budget) == records(
        path, tmp_path / "whole.sqlite", budget
    )
    assert (
        verify_interface_survey(path, tmp_path / "split.sqlite")["coverage"] == resumed["coverage"]
    )


def test_public_cli_exposes_batch_size_and_retains_skipped_diagnostics(tmp_path):
    from typer.testing import CliRunner

    from hop_design.commands.construction.survey import survey_app

    path = request_path(tmp_path)
    index = tmp_path / "cli.sqlite"
    result = CliRunner().invoke(
        survey_app,
        [
            "evaluate",
            str(path),
            "--index",
            str(index),
            "--max-evaluations",
            "1",
            "--local-nodes",
            "100",
            "--local-realizations",
            "16",
            "--release-site-pairs",
            "100",
            "--continuation-batch-size",
            "4",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["continuations_examined"] == 2
    inspected = CliRunner().invoke(survey_app, ["inspect", str(path), "--index", str(index)])
    assert inspected.exit_code == 0, inspected.output
    assert len(json.loads(inspected.output)["evaluations"][0]["skipped_empty"]) == 1


@pytest.mark.parametrize("edit", ["delete", "address", "facts", "duplicate"])
def test_rehashed_skipped_admissions_fail_molecular_replay(tmp_path, edit):
    from tests.integration.test_interface_survey_integrity import mutate

    path = request_path(tmp_path)
    index = tmp_path / "tampered.sqlite"
    evaluate_interface_survey(path, index, limits=limits(4), max_evaluations=1)

    def change(record):
        skipped = record["skipped_empty"]
        if edit == "delete":
            skipped.clear()
        elif edit == "address":
            skipped[0]["branch"] = 999
        elif edit == "facts":
            skipped[0]["local_coverage"] = {}
        else:
            skipped.append(dict(skipped[0]))

    mutate(path, index, change)
    with pytest.raises(ValueError, match="molecular replay"):
        verify_interface_survey(path, index)


def test_resume_rejects_changed_batch_size(tmp_path):
    path = request_path(tmp_path)
    index = tmp_path / "batch.sqlite"
    evaluate_interface_survey(path, index, limits=limits(4), max_evaluations=1)
    with pytest.raises(ValueError):
        evaluate_interface_survey(path, index, limits=limits(2), max_evaluations=1, resume=True)


def test_witness_after_empty_batch_retrieves_same_materials(tmp_path):
    from hop_design.design.construction.surveys.retrieve import retrieve_interface_survey_witness
    from tests.support.interface_surveys import survey_selection

    path = request_path(tmp_path)
    for name, batch, evaluations, step in (("single", 1, 2, 1), ("batch", 4, 1, 0)):
        index = tmp_path / (name + ".sqlite")
        evaluate_interface_survey(path, index, limits=limits(batch), max_evaluations=evaluations)
        retrieve_interface_survey_witness(
            path,
            index,
            selection=survey_selection(path, index, 0, step),
            destination=tmp_path / name,
        )
    assert (tmp_path / "single/preparation/oligos.csv").read_bytes() == (
        tmp_path / "batch/preparation/oligos.csv"
    ).read_bytes()
