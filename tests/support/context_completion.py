"""Finite public requests and exact checkpoint records for completion checks."""

import json
import sqlite3
from contextlib import closing

from hop_design.design.construction.surveys.completion.domains import ContextCompletionPlan
from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.design.construction.surveys.storage.blocks import BlockStore
from hop_design.design.construction.surveys.storage.legacy import ObjectStore
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
)
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
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
    with closing(sqlite3.connect(index)) as db:
        store = (
            BlockStore(db)
            if db.execute("PRAGMA user_version").fetchone()[0] == 2
            else ObjectStore(db, tracked=False)
        )
        return [
            json.loads(store.get(digest))
            for (digest,) in db.execute("SELECT record_digest FROM steps ORDER BY ordinal,step")
        ]


def legacy_checkpoint(path):
    """Make an old-layout fixture from one synthetic, single-producer checkpoint."""
    legacy = path.with_suffix(".legacy.sqlite")
    with closing(sqlite3.connect(path)) as db:
        metadata = json.loads(db.execute("SELECT content FROM metadata").fetchone()[0])
        tracked = db.execute("PRAGMA user_version").fetchone()[0] == 2
        if not tracked:
            return
        assert db.execute("SELECT COUNT(*) FROM producers").fetchone() == (1,)
        store = BlockStore(db)
        with SurveyIndex.create(
            legacy,
            request=InterfaceSurveyRequest.model_validate_json(json.dumps(metadata["request"])),
            producer=metadata["producer"],
            limits=metadata["evaluation_limits"],
            format_version=1,
        ) as target:
            for (digest,) in db.execute("SELECT digest FROM objects"):
                assert target.put_object(store.get(digest)) == digest
            for table, columns in (
                ("steps", "ordinal,step,record_digest,witness_count,exhausted,digest"),
                ("cache", "key,digest"),
            ):
                for row in db.execute(f"SELECT {columns} FROM {table}"):
                    target._db.execute(
                        f"INSERT INTO {table} VALUES ({','.join('?' for _ in row)})", row
                    )
            target._db.commit()
            target._validate()
    legacy.replace(path)


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
