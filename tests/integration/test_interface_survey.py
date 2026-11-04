"""A resumable survey retrieves ordinary complete molecular witnesses on demand."""

import json

import pytest

from hop_design.design.construction.surveys.execute import evaluate_interface_survey
from hop_design.design.construction.surveys.retrieve import retrieve_interface_survey_witness
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from tests.support.interface_surveys import survey_selection
from tests.unit.test_interface_survey_request import survey_document


def test_compact_population_budget_keeps_target_unresolved(tmp_path):
    document = survey_document()
    document["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    path = tmp_path / "survey.json"
    path.write_text(json.dumps(document))
    limits = SurveyEvaluationLimits(
        local_nodes=100,
        local_realizations=100,
        release_site_pairs=100,
        sequence_decisions=1,
    )
    result = evaluate_interface_survey(
        path, tmp_path / "survey.sqlite", limits=limits, max_evaluations=1
    )
    assert result["termination_reason"] == "sequence_space_budget"
    assert result["evaluations"] == 0
    assert result["coverage"]["unresolved_pairs"] == 1
    assert result["coverage"]["excluded_pairs"] == 0


def test_empty_complete_local_population_excludes_only_its_declared_target_scope(tmp_path):
    from hop_design.design.construction.surveys.verify import verify_interface_survey

    document = survey_document()
    document["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    document["foldback"]["geometry"].update(junction_offsets_nt=[0])
    path = tmp_path / "survey.json"
    path.write_text(json.dumps(document))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=100)
    index = tmp_path / "survey.sqlite"
    result = evaluate_interface_survey(path, index, limits=limits, max_evaluations=2)
    assert result["termination_reason"] == "exhausted_enumeration"
    assert result["evaluations"] == 1
    assert result["coverage"]["excluded_pairs"] == 1
    assert verify_interface_survey(path, index)["coverage"] == result["coverage"]


def test_compensating_placement_finds_complete_words_before_expanding_pair_roster(tmp_path):
    document = survey_document()
    document["targets"] = {"left_words": ["AAAA", "AAAC"], "right_words": ["AAAA", "AAAC"]}
    document["basal"]["annealing_lengths_nt"] = [17]
    path = tmp_path / "survey.json"
    path.write_text(json.dumps(document))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=16, release_site_pairs=100)
    result = evaluate_interface_survey(
        path, tmp_path / "survey.sqlite", limits=limits, max_evaluations=4
    )
    assert result["coverage"]["supported_pairs"] == 2
    assert result["coverage"]["unexamined_pairs"] == 2
    receipt = retrieve_interface_survey_witness(
        path,
        tmp_path / "survey.sqlite",
        selection=survey_selection(path, tmp_path / "survey.sqlite", 0, 1),
        destination=tmp_path / "selected",
    )
    assert receipt.valid_realizations == 1
    selected = json.loads((tmp_path / "selected/product-request.json").read_text())
    assert selected["ends"]["left"]["payload_end_offset_bp"] == 6
    assert selected["ends"]["right"]["payload_end_offset_bp"] == 6


def test_rejected_source_context_can_continue_to_a_complete_permitted_assignment(tmp_path):
    from hop_design.design.construction.surveys.verify import verify_interface_survey

    document = survey_document()
    document["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    document["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "CNTTGCACGTACGT"
    )
    path = tmp_path / "survey.json"
    path.write_text(json.dumps(document))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=16, release_site_pairs=100)
    first = evaluate_interface_survey(
        path, tmp_path / "survey.sqlite", limits=limits, max_evaluations=1
    )
    assert first["coverage"]["supported_pairs"] == 0
    # The next wave visits both local one-step neighbors before source context 1.
    resumed = evaluate_interface_survey(
        path, tmp_path / "survey.sqlite", limits=limits, max_evaluations=3, resume=True
    )
    assert resumed["coverage"]["supported_pairs"] == 1
    assert verify_interface_survey(path, tmp_path / "survey.sqlite")["replayed_evaluations"] == 4
    retrieve_interface_survey_witness(
        path,
        tmp_path / "survey.sqlite",
        selection=survey_selection(path, tmp_path / "survey.sqlite", 0, 3),
        destination=tmp_path / "selected",
    )
    selected = json.loads((tmp_path / "selected/product-request.json").read_text())
    assert (
        selected["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"]
        == "CCTTGCACGTACGT"
    )


def test_interrupted_full_catalogue_crosses_64_with_identical_resumed_records(
    tmp_path, monkeypatch
):
    from hop_design.design.construction.surveys import execute
    from hop_design.design.construction.surveys.index import SurveyIndex
    from hop_design.design.runtime import producer_identity

    path = tmp_path / "all-pairs.json"
    path.write_text(json.dumps(survey_document()))
    limits = SurveyEvaluationLimits(local_nodes=8, local_realizations=4, release_site_pairs=10)
    original = execute.evaluate_step
    calls = 0

    def interrupt_after_five(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 6:
            raise KeyboardInterrupt("simulated process interruption")
        return original(*args, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(execute, "evaluate_step", interrupt_after_five)
        with pytest.raises(KeyboardInterrupt):
            evaluate_interface_survey(
                path, tmp_path / "resumed.sqlite", limits=limits, max_evaluations=65
            )
    resumed = evaluate_interface_survey(
        path, tmp_path / "resumed.sqlite", limits=limits, max_evaluations=60, resume=True
    )
    whole = evaluate_interface_survey(
        path, tmp_path / "whole.sqlite", limits=limits, max_evaluations=65
    )
    assert resumed["evaluations"] == whole["evaluations"] == 65
    assert resumed["coverage"] == whole["coverage"]
    assert whole["coverage"]["target_pairs"] == 65536
    assert whole["coverage"]["unexamined_pairs"] == 65471
    bindings = {
        "request": execute.load_request(path),
        "producer": producer_identity(),
        "limits": limits.model_dump(mode="json"),
    }
    with (
        SurveyIndex.open(tmp_path / "resumed.sqlite", **bindings) as a,
        SurveyIndex.open(tmp_path / "whole.sqlite", **bindings) as b,
    ):
        assert a.last_steps() == b.last_steps()
        for target, step in a.last_steps().items():
            assert a.record(target, step=step) == b.record(target, step=step)


def test_complete_witness_survives_restart_and_on_demand_retrieval(tmp_path):
    document = survey_document()
    document["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    path = tmp_path / "survey.json"
    path.write_text(json.dumps(document))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=16, release_site_pairs=100)
    first = evaluate_interface_survey(
        path, tmp_path / "survey.sqlite", limits=limits, max_evaluations=1
    )
    assert first["coverage"]["supported_pairs"] == 1
    assert first["new_evaluations"] == 1
    assert list(tmp_path.glob("*.pdf")) == []
    second = evaluate_interface_survey(
        path, tmp_path / "survey.sqlite", limits=limits, max_evaluations=1, resume=True
    )
    assert second["coverage"]["supported_pairs"] == 1
    assert second["evaluations"] >= first["evaluations"]
    receipt = retrieve_interface_survey_witness(
        path,
        tmp_path / "survey.sqlite",
        selection=survey_selection(path, tmp_path / "survey.sqlite", 0, 0),
        destination=tmp_path / "selected",
    )
    assert receipt.endpoint == "clone_ready_duplex"
    assert receipt.valid_realizations == 1
    assert (tmp_path / "selected/preparation/oligos.csv").is_file()
    assert (tmp_path / "selected/construction/construction-bundle.json").is_file()


def test_survey_continues_local_candidates_after_one_witness_quota(tmp_path):
    document = survey_document()
    document["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    document["foldback"]["geometry"]["annealing_arm_lengths_bp"] = [9]
    document["foldback"]["max_retained_overhead_nt"] = 22
    path = tmp_path / "survey.json"
    path.write_text(json.dumps(document))
    limits = SurveyEvaluationLimits(local_nodes=10, local_realizations=1, release_site_pairs=100)
    first = evaluate_interface_survey(
        path, tmp_path / "survey.sqlite", limits=limits, max_evaluations=1
    )
    second = evaluate_interface_survey(
        path, tmp_path / "survey.sqlite", limits=limits, max_evaluations=1, resume=True
    )
    assert first["coverage"]["supported_pairs"] == 1
    assert second["new_evaluations"] == 1
    assert second["evaluations"] == 2
    assert second["unfinished_targets"] == 1


def test_branch_source_permission_conflict_is_recorded_without_losing_other_targets(tmp_path):
    document = survey_document()
    document["targets"] = {"left_words": ["AGTC", "TTTT"], "right_words": ["AGTC"]}
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    for contact in document["basal"]["geometry"]["pairing_constraints"]:
        if contact["position_from_ligation"] == 6:
            contact["allowed_source_bases"] = ["A"]
    path = tmp_path / "survey.json"
    path.write_text(json.dumps(document))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=16, release_site_pairs=100)
    result = evaluate_interface_survey(
        path, tmp_path / "survey.sqlite", limits=limits, max_evaluations=2
    )
    assert result["coverage"]["unexamined_pairs"] == 0
    from hop_design.design.construction.surveys.execute import load_request
    from hop_design.design.construction.surveys.index import SurveyIndex
    from hop_design.design.runtime import producer_identity

    with SurveyIndex.open(
        tmp_path / "survey.sqlite",
        request=load_request(path),
        producer=producer_identity(),
        limits=limits.model_dump(mode="json"),
    ) as index:
        rejected = json.loads(index.record(1, step=0))
    assert rejected["rejection"]["code"] == "end_source_base_conflict"
    assert rejected["rejection"]["position_from_ligation"] == 6
    assert rejected["witnesses"] == []
    assert rejected["exhaustion_proven"] is True
