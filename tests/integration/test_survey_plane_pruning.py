"""Recorded complete-local exclusions survive public execution, resume and replay."""

import json

import pytest

from hop_design import construction
from hop_design.design.construction.surveys.admission import open_survey
from hop_design.design.construction.surveys.execute import load_request
from hop_design.design.runtime import producer_identity
from tests.unit.test_interface_survey_request import survey_document


def request_file(tmp_path):
    data = survey_document()
    data["placements"] = [{"left_bp": 0, "right_bp": 0}]
    data["basal"]["annealing_lengths_nt"] = [10]
    data["foldback"]["geometry"]["loop_lengths_nt"] = [4, 5]
    data["foldback"]["max_retained_overhead_nt"] = 17
    data["targets"] = {"left_words": ["AAAA", "TTTT"], "right_words": ["AAAA"]}
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "ACGTACAGTCGTAN"
    )
    path = tmp_path / "request.json"
    path.write_text(json.dumps(data))
    return path


def execute(path, index, count, resume=False, navigation_nodes=1):
    return construction.evaluate_interface_survey(
        path,
        index,
        max_evaluations=count,
        local_nodes=100,
        local_realizations=100,
        release_site_pairs=10,
        navigation_nodes=navigation_nodes,
        resume=resume,
    )


def records(path, index):
    saved, _ = open_survey(index, request=load_request(path), producer=producer_identity())
    with saved:
        return [json.loads(row[2]) for row in saved.evaluations()]


def test_complete_empty_plane_excludes_free_axes_with_one_recorded_molecular_admission(tmp_path):
    path = request_file(tmp_path)
    index = tmp_path / "survey.sqlite"
    report = execute(path, index, 2)
    assert report["coverage"]["excluded_pairs"] == 2
    assert report["continuations_examined"] == 2
    assert report["certified_empty_planes"] == 2
    assert report["certified_empty_branch_cells"] == 16
    saved = records(path, index)
    assert len(saved) == 2
    assert all(len(r["empty_basal_planes"]) == 1 for r in saved)
    assert all(r["next"] is None for r in saved)
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 2


def test_resumption_and_different_target_interleaving_preserve_records(tmp_path):
    path = request_file(tmp_path)
    whole, resumed = tmp_path / "whole.sqlite", tmp_path / "resumed.sqlite"
    execute(path, whole, 2)
    first = execute(path, resumed, 1)
    assert first["coverage"]["excluded_pairs"] == 1
    execute(path, resumed, 1, resume=True)
    assert records(path, whole) == records(path, resumed)
    assert construction.verify_interface_survey(path, resumed)["coverage"]["excluded_pairs"] == 2


def test_navigation_only_progress_has_no_invented_molecular_attempt(tmp_path):
    path = request_file(tmp_path)
    data = json.loads(path.read_text())
    data["placements"].append({"left_bp": 6, "right_bp": 6})
    data["basal"]["annealing_lengths_nt"] = [17]
    data["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    path.write_text(json.dumps(data))
    index = tmp_path / "survey.sqlite"
    report = execute(path, index, 8)
    saved = records(path, index)
    seek = [r for r in saved if r["schema"] == "hop.interface-survey-navigation/v1"]
    assert seek
    assert all(r["continuations_examined"] == 0 and not r["witnesses"] for r in seek)
    assert report["continuations_examined"] == sum(r["continuations_examined"] for r in saved)
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == len(saved)
    inspected = construction.inspect_interface_survey(path, index)
    assert len(inspected["evaluations"]) == len(saved)


def test_rehashed_certificate_tampering_is_rejected_on_resume_and_replay(tmp_path):
    import pytest

    from hop_design.design.construction.surveys.index import SurveyIndex
    from hop_design.serialization import canonical_json_bytes

    path = request_file(tmp_path)
    original, corrupt = tmp_path / "original.sqlite", tmp_path / "corrupt.sqlite"
    execute(path, original, 1)
    request = load_request(path)
    source, limits = open_survey(original, request=request, producer=producer_identity())
    with (
        source,
        SurveyIndex.create(
            corrupt,
            request=request,
            producer=producer_identity(),
            limits=limits.model_dump(mode="json"),
        ) as target,
    ):
        saved = json.loads(source.record(0, step=0))
        target.put_object(source.get_object(saved["product_request"]))
        proof = json.loads(source.get_object(saved["empty_basal_planes"][0]))
        proof["facts"]["program_count"] += 1
        saved["empty_basal_planes"] = [target.put_object(canonical_json_bytes(proof))]
        target.append(
            0, step=0, record=canonical_json_bytes(saved), witness_count=0, exhausted=True
        )
    with pytest.raises(ValueError, match="replay"):
        execute(path, corrupt, 1, resume=True)
    with pytest.raises(ValueError, match="replay"):
        construction.verify_interface_survey(path, corrupt)


def test_cli_and_api_keep_the_same_navigation_budget_and_proof_records(tmp_path):
    from typer.testing import CliRunner

    from hop_design.cli import app

    path = request_file(tmp_path)
    api, cli = tmp_path / "api.sqlite", tmp_path / "cli.sqlite"
    execute(path, api, 2)
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "survey",
            "evaluate",
            str(path),
            "--index",
            str(cli),
            "--max-evaluations",
            "2",
            "--local-nodes",
            "100",
            "--local-realizations",
            "100",
            "--release-site-pairs",
            "10",
            "--navigation-nodes",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert records(path, api) == records(path, cli)


@pytest.mark.parametrize("supported", [False, True])
def test_completed_evidence_commits_before_a_later_navigation_budget_stop(
    tmp_path, monkeypatch, supported
):
    from hop_design.design.construction.surveys import evaluate
    from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError

    path = request_file(tmp_path)
    data = json.loads(path.read_text())
    if supported:
        data["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
        data["placements"] = [{"left_bp": 6, "right_bp": 6}]
        data["basal"]["annealing_lengths_nt"] = [17]
    path.write_text(json.dumps(data))
    index = tmp_path / "survey.sqlite"

    def exhausted(*args, **kwargs):
        raise SequenceSetLimitError("next geometry exceeds the admission budget")

    monkeypatch.setattr(evaluate, "advance", exhausted)
    report = execute(path, index, 1)
    saved = records(path, index)
    assert report["new_evaluations"] == 1 and len(saved) == 1
    assert "seek" in saved[0]["next"]
    assert saved[0]["navigation_stop"] == "sequence_space_budget"
    assert saved[0]["navigation_nodes_complete"] is False
    row = construction.inspect_interface_survey(path, index)["evaluations"][0]
    assert row["navigation_nodes_complete"] is False
    assert row["navigation_stop"] == "sequence_space_budget"
    assert bool(saved[0]["witnesses"]) is supported
    assert len(saved[0]["empty_basal_planes"]) == int(not supported)
