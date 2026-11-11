"""Content conversion preserves the prefix without rerunning discovery."""

import json

import pytest

from hop_design import construction
from hop_design.design.construction.surveys.storage.migration import migrate_interface_survey
from tests.support.context_completion import LIMITS, legacy_checkpoint, records, request
from tests.support.interface_surveys import indexed_survey, survey_selection


def permit_synthetic_transition(monkeypatch, source):
    from hop_design.design import runtime
    from hop_design.design.construction.surveys.storage import compatibility

    target = runtime.producer_identity()
    policy = {
        "schema": "hop.survey-compatibility/v1",
        "declarations": [
            {
                "source_version": source["package_version"],
                "source_content": source["package_content"],
                "target_version": target["package_version"],
                "target_code": target["package_code"],
                "computation_contract": "interface-survey/1",
            }
        ],
    }
    monkeypatch.setattr(compatibility, "_policy_bytes", lambda: json.dumps(policy).encode())


def test_same_producer_migration_preserves_selection_and_continues(tmp_path, monkeypatch):
    from hop_design.design.construction.surveys import replay

    path, source = indexed_survey(tmp_path)
    legacy_checkpoint(source)
    selection = survey_selection(path, source, target=0, step=0)
    old = source.read_bytes()
    original_records = records(source)

    def no_solver(*args, **kwargs):
        raise AssertionError("Storage conversion cannot rerun historical molecular search.")

    with monkeypatch.context() as patch:
        patch.setattr(replay, "replay_evaluations", no_solver)
        report = migrate_interface_survey(path, source, destination=tmp_path / "migrated")
    target = tmp_path / "migrated/survey.sqlite"
    assert source.read_bytes() == old
    assert records(target) == original_records
    assert report["verification"] == "lossless_content_conversion"
    assert report["source_logical_digest"] == report["retained_prefix_digest"]
    assert report["evaluations"] == 1
    assert report["source_format"] == 1 and report["target_format"] == 2
    assert json.loads((target.parent / "migration.json").read_text()) == report
    construction.retrieve_interface_survey_witness(
        path, target, selection=selection, destination=tmp_path / "handoff"
    )
    construction.evaluate_interface_survey(
        path, target, max_evaluations=1, resume=True, **{**LIMITS, "local_realizations": 16}
    )
    assert records(target)[:1] == original_records
    assert construction.verify_interface_survey(path, target)["replayed_evaluations"] == 2


def test_cancelled_conversion_preserves_source_and_publishes_no_target(tmp_path):
    path = request(tmp_path, "source", completion=True)
    source = tmp_path / "old.sqlite"
    construction.evaluate_interface_survey(path, source, max_evaluations=1, **LIMITS)
    before = source.read_bytes()
    with pytest.raises(InterruptedError, match="cancel"):
        migrate_interface_survey(
            path, source, destination=tmp_path / "migrated", should_stop=lambda: True
        )
    assert source.read_bytes() == before
    assert not (tmp_path / "migrated").exists()
    assert not list(tmp_path.glob(".migrated.*"))


def test_declared_version_change_keeps_old_selection_and_new_creator(tmp_path, monkeypatch):
    from hop_design.design import runtime
    from hop_design.design.construction.surveys.admission import open_survey
    from hop_design.design.construction.surveys.execute import load_request

    # These are synthetic releases of the same test kernel. Production accepts
    # only pairs shipped in HOP's package-bound compatibility policy.
    installed = runtime.version
    with monkeypatch.context() as old_context:
        old_context.setattr(
            runtime, "version", lambda name: "0.0.1" if name == "hop-design" else installed(name)
        )
        path, source = indexed_survey(tmp_path)
        selection = survey_selection(path, source, target=0, step=0)
        original = runtime.producer_identity()
    before = source.read_bytes()
    permit_synthetic_transition(monkeypatch, original)
    migrate_interface_survey(path, source, destination=tmp_path / "migrated")
    target = tmp_path / "migrated/survey.sqlite"
    construction.retrieve_interface_survey_witness(
        path, target, selection=selection, destination=tmp_path / "old-handoff"
    )
    effort = {**LIMITS, "local_realizations": 16}
    construction.evaluate_interface_survey(path, target, max_evaluations=2, resume=True, **effort)
    saved, _ = open_survey(target, request=load_request(path), producer=runtime.producer_identity())
    with saved:
        assert saved.step_creator(0, step=0) == original
        newer = [
            saved.step_creator(t, step=s) for t, s, *_ in saved.evaluations() if (t, s) != (0, 0)
        ]
        assert newer and all(p == runtime.producer_identity() for p in newer)
    assert source.read_bytes() == before
    assert construction.verify_interface_survey(path, target)["replayed_evaluations"] == 3


def test_old_and_new_exclusion_proofs_survive_cold_continuation(tmp_path, monkeypatch):
    from hop_design.design import runtime
    from tests.integration.test_survey_plane_pruning import execute, request_file

    path = request_file(tmp_path)
    source = tmp_path / "old.sqlite"
    installed = runtime.version
    with monkeypatch.context() as old_context:
        old_context.setattr(
            runtime, "version", lambda name: "0.0.1" if name == "hop-design" else installed(name)
        )
        execute(path, source, 1)
        original = runtime.producer_identity()
    permit_synthetic_transition(monkeypatch, original)
    migrate_interface_survey(path, source, destination=tmp_path / "migrated")
    target = tmp_path / "migrated/survey.sqlite"
    assert execute(path, target, 1, resume=True)["coverage"]["excluded_pairs"] == 2
    assert execute(path, target, 1, resume=True)["new_evaluations"] == 0
    assert construction.verify_interface_survey(path, target)["replayed_evaluations"] == 2
