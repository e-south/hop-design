"""The existing public survey API can enumerate scaffolds with exact handle witnesses."""

import json

import pytest

from hop_design import construction
from tests.support.context_completion import LIMITS, records, request


def test_public_completion_matches_exhaustive_product_choices_with_fewer_attempts(tmp_path):
    outcomes, rows = {}, {}
    for mode in (True, False):
        path = request(tmp_path, str(mode), completion=mode)
        index = tmp_path / f"{mode}.sqlite"
        outcomes[mode] = construction.evaluate_interface_survey(
            path,
            index,
            max_evaluations=300,
            **LIMITS,
        )
        rows[mode] = records(index)
        assert outcomes[mode]["termination_reason"] == "exhausted_enumeration"

    def endpoints(mode):
        return {p["molecular_identity"]["endpoint"] for r in rows[mode] for p in r["projections"]}

    def preparations(mode):
        return {w for r in rows[mode] for w in r["witnesses"]}

    assert endpoints(True) and endpoints(True) == endpoints(False)
    assert preparations(True) <= preparations(False)
    assert sum(r["bundle"] is not None for r in rows[True]) < sum(
        r["bundle"] is not None for r in rows[False]
    )
    assert outcomes[True]["enumeration_scope"] == "paired_scaffold_completions"
    replay = construction.verify_interface_survey(tmp_path / "True.json", tmp_path / "True.sqlite")
    assert replay["coverage"] == outcomes[True]["coverage"]
    pool = construction.load_interface_survey_choices(
        tmp_path / "True.json", tmp_path / "True.sqlite"
    )
    projection = pool.query()
    assert projection["fully_enumerated"]
    assert projection["enumeration_scope"] == "paired_scaffold_completions"
    assert projection["all_preparations_enumerated"] is False


def test_failed_first_handle_remains_unresolved_and_resumes_to_same_exact_witness(tmp_path):
    path = request(tmp_path, "resume", completion=True)
    data = json.loads(path.read_text())
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "CWTTGCAGTCGTAC"
    )
    path.write_text(json.dumps(data))
    index, full = tmp_path / "resume.sqlite", tmp_path / "uninterrupted.sqlite"
    first = construction.evaluate_interface_survey(path, index, max_evaluations=2, **LIMITS)
    assert first["coverage"]["supported_pairs"] == first["coverage"]["excluded_pairs"] == 0
    assert first["coverage"]["unresolved_pairs"] == 1
    attempted = records(index)[-1]
    assert attempted["outcome"]["rejection_reasons"] == ["global-actionable-site-conflict"]
    pending = [
        e["work"] for e in attempted["next"]["completion_seek"]["frontier"] if e["kind"] == "work"
    ]
    assert any(w["pair"] == 0 and w["member"] == 1 for w in pending)
    assert not attempted["group_pair_resolved"]
    later = construction.evaluate_interface_survey(
        path, index, max_evaluations=2, resume=True, **LIMITS
    )
    assert later["coverage"]["supported_pairs"] == 1
    construction.evaluate_interface_survey(path, full, max_evaluations=4, **LIMITS)
    assert records(index) == records(full)
    assert construction.verify_interface_survey(path, index)["replayed_evaluations"] == 4


def test_rehashed_group_cursor_is_rejected_by_molecular_replay(tmp_path):
    from hop_design.design.construction.surveys.admission import open_survey
    from hop_design.design.construction.surveys.execute import load_request
    from hop_design.design.construction.surveys.index import SurveyIndex
    from hop_design.design.runtime import producer_identity
    from hop_design.serialization import canonical_json_bytes

    path = request(tmp_path, "tamper", completion=True)
    original, corrupt = tmp_path / "original.sqlite", tmp_path / "corrupt.sqlite"
    construction.evaluate_interface_survey(path, original, max_evaluations=1, **LIMITS)
    parsed, producer = load_request(path), producer_identity()
    source, limits = open_survey(original, request=parsed, producer=producer)
    with (
        source,
        SurveyIndex.create(
            corrupt,
            request=parsed,
            producer=producer,
            limits=limits.model_dump(mode="json"),
        ) as target,
    ):
        saved = json.loads(source.record(0, step=0))
        saved["next"]["completion"]["member"] += 1
        target.append(
            0, step=0, record=canonical_json_bytes(saved), witness_count=0, exhausted=False
        )
    with pytest.raises(ValueError, match="molecular replay"):
        construction.verify_interface_survey(path, corrupt)


def test_public_frontier_limit_leaves_the_target_unresolved(tmp_path):
    path = request(tmp_path, "frontier-limit", completion=True)
    outcome = construction.evaluate_interface_survey(
        path,
        tmp_path / "limited.sqlite",
        max_evaluations=3,
        navigation_frontier=1,
        **LIMITS,
    )
    assert outcome["termination_reason"] == "navigation_frontier_budget"
    assert outcome["coverage"]["supported_pairs"] == 0
    assert outcome["coverage"]["excluded_pairs"] == 0
    assert outcome["coverage"]["unresolved_pairs"] == 1
