"""Execution and replay use the same invertible first-address preference."""

import json
from types import SimpleNamespace

from hop_design.design.construction.surveys.execute import evaluate_interface_survey, load_request
from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.design.construction.surveys.verify import verify_interface_survey
from hop_design.design.runtime import producer_identity
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from tests.unit.test_interface_survey_request import survey_document


def request(tmp_path):
    document = survey_document()
    document["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    document["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "ACGTACAGTCGTAN"
    )
    path = tmp_path / "request.json"
    path.write_text(json.dumps(document))
    return path


def test_conditioned_first_page_is_used_by_execution_resume_and_replay(tmp_path, monkeypatch):
    # The independently tested molecular conditioner supplies a permutation.
    # Here an explicit four-member permutation tests the execution/replay seam.
    # Local and complete molecular evaluation remains real.
    values = (2, 0, 3, 1)

    def priority(self, product, page, policy):
        self._contexts.clear()  # Cache history must not affect committed addresses.
        return SimpleNamespace(rank_at=values.__getitem__, position=values.index)

    monkeypatch.setattr(PartitionPlans, "context_priority", priority)
    path = request(tmp_path)
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=100)
    split_path, whole_path = tmp_path / "split.sqlite", tmp_path / "whole.sqlite"
    evaluate_interface_survey(path, split_path, limits=limits, max_evaluations=1)
    split = evaluate_interface_survey(
        path, split_path, limits=limits, max_evaluations=2, resume=True
    )
    whole = evaluate_interface_survey(path, whole_path, limits=limits, max_evaluations=3)
    assert split["coverage"] == whole["coverage"]
    bindings = {
        "request": load_request(path),
        "producer": producer_identity(),
        "limits": limits.model_dump(mode="json"),
    }
    with (
        SurveyIndex.open(split_path, **bindings) as a,
        SurveyIndex.open(whole_path, **bindings) as b,
    ):
        rows = [a.record(0, step=i) for i in range(3)]
        assert rows == [b.record(0, step=i) for i in range(3)]
        assert json.loads(rows[0])["branch"] == 2
        product = json.loads(a.get_object(json.loads(rows[0])["product_request"]))
        assert (
            product["materialization"]["source_preparation"]["source_ssdna"][
                "upstream_sequence_spec"
            ]
            == "ACGTACAGTCGTAG"
        )
    assert verify_interface_survey(path, split_path)["replayed_evaluations"] == 3


def test_initial_population_resource_stop_leaves_target_unexamined(tmp_path, monkeypatch):
    def exceeded(*args, **kwargs):
        raise SequenceSetLimitError("initial local population budget")

    monkeypatch.setattr(PartitionPlans, "first_page", exceeded)
    path = request(tmp_path)
    result = evaluate_interface_survey(
        path,
        tmp_path / "limited.sqlite",
        limits=SurveyEvaluationLimits(
            local_nodes=100, local_realizations=100, release_site_pairs=100
        ),
        max_evaluations=1,
    )
    assert result["termination_reason"] == "sequence_space_budget"
    assert result["evaluations"] == 0
    assert result["coverage"]["unexamined_pairs"] == 1
    assert result["coverage"]["excluded_pairs"] == 0
