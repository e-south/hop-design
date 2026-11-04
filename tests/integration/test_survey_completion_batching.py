"""Completion mode must use the declared work batch before reporting progress."""

import json

from hop_design import construction
from tests.support.context_completion import LIMITS, records, request


def test_batch_reaches_a_complete_preparation_instead_of_committing_only_navigation(tmp_path):
    path = request(tmp_path, "batch", completion=True)
    index = tmp_path / "batch.sqlite"
    result = construction.evaluate_interface_survey(
        path, index, max_evaluations=1, continuation_batch_size=64, **LIMITS
    )
    assert result["coverage"]["supported_pairs"] == 1
    assert result["new_continuations_examined"] == 1
    row = records(index)[0]
    assert row["bundle"] is not None
    assert row["preceding_completion_steps"]
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 1


def test_failed_completion_stops_the_batch_without_hiding_its_rejection(tmp_path):
    path = request(tmp_path, "failure", completion=True)
    data = json.loads(path.read_text())
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "CWTTGCAGTCGTAC"
    )
    path.write_text(json.dumps(data))
    index = tmp_path / "failure.sqlite"
    first = construction.evaluate_interface_survey(
        path, index, max_evaluations=1, continuation_batch_size=64, **LIMITS
    )
    assert first["coverage"]["supported_pairs"] == 0
    row = records(index)[0]
    assert row["outcome"]["rejection_reasons"] == ["global-actionable-site-conflict"]
    assert first["new_continuations_examined"] == 1
    assert first["coverage"]["unresolved_pairs"] == 1
    later = construction.evaluate_interface_survey(
        path, index, max_evaluations=1, continuation_batch_size=64, resume=True, **LIMITS
    )
    assert later["coverage"]["supported_pairs"] == 1
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 2


def test_batch_preserves_every_complete_choice_and_reduces_commits(tmp_path):
    path = request(tmp_path, "parity", completion=True)
    outcomes = []
    seen = []
    for batch in (1, 64):
        index = tmp_path / f"batch-{batch}.sqlite"
        result = construction.evaluate_interface_survey(
            path, index, max_evaluations=300, continuation_batch_size=batch, **LIMITS
        )
        assert result["termination_reason"] == "exhausted_enumeration"
        outcomes.append(result)
        seen.append({w for row in records(index) for w in row["witnesses"]})
    assert len(seen[0]) == 16 and seen[0] == seen[1]
    assert outcomes[1]["evaluations"] < outcomes[0]["evaluations"]
    assert outcomes[1]["continuations_examined"] == outcomes[0]["continuations_examined"]
    replay = construction.verify_interface_survey(path, tmp_path / "batch-64.sqlite")
    assert replay["coverage"] == outcomes[1]["coverage"]


def empty_then_supported(tmp_path):
    path = request(tmp_path, "empty-first", completion=True)
    data = json.loads(path.read_text())
    data["placements"] = [{"left_bp": 0, "right_bp": 0}, {"left_bp": 6, "right_bp": 6}]
    path.write_text(json.dumps(data))
    return path


def test_cold_resume_recomputes_necessary_relations_inside_the_batch(tmp_path):
    path = empty_then_supported(tmp_path)
    resumed = tmp_path / "resumed.sqlite"
    full = tmp_path / "continuous.sqlite"
    first = construction.evaluate_interface_survey(
        path, resumed, max_evaluations=1, continuation_batch_size=64, **LIMITS
    )
    row = records(resumed)[0]
    assert not row["empty_basal_planes"]
    import sqlite3
    import zlib

    with sqlite3.connect(resumed) as db:
        prelude = [
            json.loads(
                zlib.decompress(
                    db.execute("SELECT content FROM objects WHERE digest=?", (digest,)).fetchone()[
                        0
                    ]
                )
            )
            for digest in row["preceding_completion_steps"]
        ]
    assert any(
        not facts["requested_pair_admitted"]
        for step in prelude
        for facts in step.get("end_pair_admission", {}).values()
    )
    assert first["coverage"]["supported_pairs"] == 1
    construction.evaluate_interface_survey(
        path, resumed, max_evaluations=1, continuation_batch_size=64, resume=True, **LIMITS
    )
    construction.evaluate_interface_survey(
        path, full, max_evaluations=2, continuation_batch_size=64, **LIMITS
    )
    assert records(resumed) == records(full)
    assert construction.verify_interface_survey(path, resumed)["replayed_evaluations"] == 2


def test_navigation_node_allowance_is_not_silently_multiplied_by_batch_size(tmp_path):
    path = request(tmp_path, "nodes", completion=True)
    index = tmp_path / "nodes.sqlite"
    result = construction.evaluate_interface_survey(
        path, index, max_evaluations=1, navigation_nodes=1, continuation_batch_size=64, **LIMITS
    )
    assert result["coverage"]["supported_pairs"] == 0
    row = records(index)[0]
    assert row["navigation_nodes"] == 1
    assert row["continuations_examined"] == 0
    assert "completion_seek" in row["next"]


def test_replay_rejects_resealed_necessary_relation_from_preceding_step(tmp_path):
    import sqlite3
    import zlib

    import pytest

    from hop_design.serialization import canonical_json_bytes, sha256_digest

    path = empty_then_supported(tmp_path)
    index = tmp_path / "tamper.sqlite"
    construction.evaluate_interface_survey(
        path, index, max_evaluations=1, continuation_batch_size=64, **LIMITS
    )
    row = records(index)[0]
    with sqlite3.connect(index) as db:
        for digest in row["preceding_completion_steps"]:
            prior = json.loads(
                zlib.decompress(
                    db.execute("SELECT content FROM objects WHERE digest=?", (digest,)).fetchone()[
                        0
                    ]
                )
            )
            rejected = next(
                (
                    f
                    for f in prior.get("end_pair_admission", {}).values()
                    if not f["requested_pair_admitted"]
                ),
                None,
            )
            if rejected is None:
                continue
            rejected["requested_pair_admitted"] = True
            raw = canonical_json_bytes(prior)
            changed = sha256_digest(raw)
            db.execute("INSERT INTO objects VALUES (?, ?)", (changed, zlib.compress(raw)))
            row["preceding_completion_steps"] = [
                changed if d == digest else d for d in row["preceding_completion_steps"]
            ]
            raw = canonical_json_bytes(row)
            changed = sha256_digest(raw)
            db.execute("INSERT INTO objects VALUES (?, ?)", (changed, zlib.compress(raw)))
            db.execute("UPDATE steps SET record_digest=?", (changed,))
            step = db.execute(
                "SELECT ordinal,step,record_digest,witness_count,exhausted FROM steps"
            ).fetchone()
            db.execute("UPDATE steps SET digest=?", (sha256_digest(canonical_json_bytes(step)),))
            break
        else:
            pytest.fail("Expected a recorded necessary end-pair exclusion")
    with pytest.raises(ValueError, match="failed molecular replay"):
        construction.verify_interface_survey(path, index)
