"""Context scheduling changes traversal while preserving canonical replay addresses."""

import json

from hop_design.design.construction.surveys.execute import evaluate_interface_survey, load_request
from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.design.construction.surveys.verify import verify_interface_survey
from hop_design.design.runtime import producer_identity
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from tests.unit.test_interface_survey_request import survey_document


def test_permuted_contexts_resume_and_replay_with_identical_records(tmp_path):
    document = survey_document()
    document["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    document["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = {
        "min_length_nt": 14,
        "max_length_nt": 15,
        "base_spec": "R",
    }
    path = tmp_path / "request.json"
    path.write_text(json.dumps(document))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=100)
    evaluate_interface_survey(path, tmp_path / "split.sqlite", limits=limits, max_evaluations=2)
    split = evaluate_interface_survey(
        path, tmp_path / "split.sqlite", limits=limits, max_evaluations=4, resume=True
    )
    whole = evaluate_interface_survey(
        path, tmp_path / "whole.sqlite", limits=limits, max_evaluations=6
    )
    assert split["evaluations"] == whole["evaluations"] == 6
    assert split["coverage"] == whole["coverage"]
    bindings = {
        "request": load_request(path),
        "producer": producer_identity(),
        "limits": limits.model_dump(mode="json"),
    }
    with (
        SurveyIndex.open(tmp_path / "split.sqlite", **bindings) as a,
        SurveyIndex.open(tmp_path / "whole.sqlite", **bindings) as b,
    ):
        rows = [a.record(0, step=step) for step in range(6)]
        assert rows == [b.record(0, step=step) for step in range(6)]
        lengths = set()
        for raw in rows:
            data = json.loads(raw)
            product = json.loads(a.get_object(data["product_request"]))
            lengths.add(
                len(
                    product["materialization"]["source_preparation"]["source_ssdna"][
                        "upstream_sequence_spec"
                    ]
                )
            )
        assert lengths == {14, 15}
    assert verify_interface_survey(path, tmp_path / "split.sqlite")["replayed_evaluations"] == 6
