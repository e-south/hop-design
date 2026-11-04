"""Explicit selection of an existing survey address for replay tests."""

import json

from hop_design import construction
from tests.unit.test_interface_survey_request import survey_document


def survey_selection(request, index, target, step):
    pool = construction.load_interface_survey_choices(request, index)
    path = next(
        p for p in pool.query()["paths"] if p["address"] == {"target": target, "step": step}
    )
    return pool.select(
        target=target, step=step, materialized_realization_id=path["materialized_realization_id"]
    )


def indexed_survey(tmp_path):
    document = survey_document()
    document["targets"] = {"left_words": ["AGTC", "TGCA"], "right_words": ["AGTC"]}
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    path = tmp_path / "request.json"
    path.write_text(json.dumps(document))
    index = tmp_path / "survey.sqlite"
    construction.evaluate_interface_survey(
        path,
        index,
        max_evaluations=1,
        local_nodes=100,
        local_realizations=16,
        release_site_pairs=100,
    )
    return path, index
