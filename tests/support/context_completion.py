"""Finite public requests and exact checkpoint records for completion checks."""

import json
import sqlite3
import zlib

from hop_design.design.construction.surveys.completion.domains import ContextCompletionPlan
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
)
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.unit.test_interface_survey_request import survey_document

LIMITS = {"local_nodes": 100, "local_realizations": 100, "release_site_pairs": 100}


def request(tmp_path, name, *, completion):
    data = survey_document()
    data["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    data["placements"] = [{"left_bp": 6, "right_bp": 6}]
    data["basal"]["annealing_lengths_nt"] = [17]
    data["foldback"]["geometry"]["loop_sequences"] = ["AAAG"]
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "NCGTACAGTCGTAC"
    )
    if completion:
        data["source_context_objective"] = "paired_scaffold_completions"
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(data))
    return path


def records(index):
    with sqlite3.connect(index) as db:
        return [
            json.loads(zlib.decompress(content))
            for (content,) in db.execute(
                "SELECT objects.content FROM steps JOIN objects ON record_digest=objects.digest "
                "ORDER BY ordinal,step"
            )
        ]


def policy(spec):
    return ConstrainedSourceSsdnaPolicy.model_validate_json(
        json.dumps(
            {
                "mode": "constrain",
                "upstream_sequence_spec": spec,
                "five_prime_end": "hydroxyl",
                "three_prime_end": "hydroxyl",
            }
        )
    )


def plan(spec, protected):
    return ContextCompletionPlan.create(
        policy(spec),
        protected_suffix_nt=protected,
        limits=DEFAULT_SEQUENCE_LIMITS,
    )
