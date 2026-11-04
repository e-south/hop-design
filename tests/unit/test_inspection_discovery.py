"""Browser search is a separate owned branch, never a mutation of the inspected pool."""

import json
import multiprocessing
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from hop_design.commands.design.inspection_discovery import DiscoveryWork, default_request

REQUEST = {"stem_arm": "ACGTACGT", "product": "hairpin"}


@pytest.fixture(autouse=True)
def spawn_import_path(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))


def cooperative_worker(connection, stopped, directory, request, evaluations, first_choices):
    Path(directory).mkdir(parents=True, exist_ok=True)
    progress = {
        "schema": "hop.discovery-progress/v1",
        "product": "hairpin",
        "phase": "checkpointed",
        "evaluations": 1,
        "new_evaluations": 1,
        "evaluation_budget": evaluations,
        "termination_reason": None,
    }
    connection.send({"kind": "progress", "progress": progress})
    stopped.wait(10)
    progress.update(phase="stopped", termination_reason="cancelled")
    connection.send({"kind": "progress", "progress": progress})
    connection.send(
        {
            "kind": "finished",
            "status": "cancelled",
            "message": None,
            "resumable": True,
            "matching_preparations": 1,
        }
    )
    connection.close()


def zero_worker(connection, stopped, directory, request, evaluations, first_choices):
    Path(directory).mkdir(parents=True, exist_ok=True)
    connection.send(
        {
            "kind": "finished",
            "status": "cancelled",
            "message": "Stopped before a first result snapshot.",
            "resumable": True,
        }
    )
    connection.close()


def failed_worker(connection, stopped, directory, request, evaluations, first_choices):
    connection.send(
        {"kind": "finished", "status": "failed", "message": "bad permissions", "resumable": False}
    )
    connection.close()


def unresponsive_worker(connection, stopped, directory, request, evaluations, first_choices):
    connection.send({"kind": "progress", "progress": {"evaluations": 0}})
    time.sleep(30)


def authored_request_worker(connection, stopped, directory, request, evaluations, first_choices):
    Path(directory).mkdir(parents=True, exist_ok=True)
    (Path(directory) / "authored-request.json").write_text(json.dumps(request))
    connection.send(
        {
            "kind": "finished",
            "status": "completed",
            "message": None,
            "resumable": False,
            "matching_preparations": 0,
        }
    )
    connection.close()


def wait_for(work, predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        status = work.snapshot()
        if predicate(status):
            return status
        time.sleep(0.01)
    pytest.fail(f"Timed out waiting for discovery: {work.snapshot()}")


def test_work_is_bounded_cancelable_and_keeps_committed_counts(tmp_path):
    children = {p.pid for p in multiprocessing.active_children()}
    work = DiscoveryWork(tmp_path, worker=cooperative_worker)
    try:
        job = work.begin(REQUEST, evaluations=3)
        assert Path(job["directory"]).is_relative_to(tmp_path)
        with pytest.raises(ValueError, match="already running"):
            work.begin(REQUEST, evaluations=3)
        progress = wait_for(work, lambda s: s["progress"] is not None)
        assert progress["progress"]["new_evaluations"] == 1
        assert work.stop(job["id"])["status"] == "stopping"
        work.stop(job["id"])  # Idempotent while stopping.
        result = wait_for(work, lambda s: s["status"] == "cancelled")
        assert result["progress"]["evaluations"] == 1
        assert result["can_continue"]
        assert "design view" in result["command"]
        assert work.stop(job["id"]) == result  # Idempotent after cancellation.
        resumed = work.begin(None, evaluations=2, previous=job["id"])
        assert resumed["id"] != job["id"]
        assert resumed["directory"] == job["directory"]
        with pytest.raises(ValueError, match="superseded"):
            work.stop(job["id"])
    finally:
        work.close()
    assert {p.pid for p in multiprocessing.active_children()} == children


@pytest.mark.parametrize("worker,status", [(zero_worker, "cancelled"), (failed_worker, "failed")])
def test_zero_work_and_failure_do_not_become_exclusions(tmp_path, worker, status):
    work = DiscoveryWork(tmp_path, worker=worker)
    try:
        work.begin(REQUEST, evaluations=2)
        result = wait_for(work, lambda s: s["status"] == status)
        assert result["progress"] is None
        assert "excluded" not in result
        assert result["can_continue"] is (status == "cancelled")
    finally:
        work.close()


def test_closed_work_and_stale_ids_cannot_start_or_stop_another_job(tmp_path):
    work = DiscoveryWork(tmp_path, worker=zero_worker)
    with pytest.raises(ValueError, match="superseded"):
        work.stop("not-owned")
    work.close()
    with pytest.raises(ValueError, match="closed"):
        work.begin(REQUEST)


def test_close_reaps_an_unresponsive_worker_without_claiming_completion(tmp_path):
    children = {p.pid for p in multiprocessing.active_children()}
    work = DiscoveryWork(tmp_path, worker=unresponsive_worker)
    work.begin(REQUEST)
    wait_for(work, lambda status: status["progress"] is not None)
    began = time.monotonic()
    work.close()
    assert time.monotonic() - began < 5
    assert work.snapshot()["status"] == "interrupted"
    assert not work.snapshot()["can_continue"]
    assert {p.pid for p in multiprocessing.active_children()} == children


def test_portable_request_preserves_inline_permissions_and_rejects_family():
    permissions = {"schema": "hop.construction-context/v1", "context_id": "example/v1"}
    resolution = {
        "schema": "hop.resolved-design-request/v1",
        "intent": REQUEST,
        "permissions": permissions,
    }
    actual = default_request(resolution)
    assert actual == {**REQUEST, "context": permissions}
    actual["context"]["context_id"] = "changed"
    assert permissions["context_id"] == "example/v1"
    assert default_request({"schema": "hop.design-family-preview/v1"}) is None


def test_default_branch_omits_only_old_preparation_order_pointers():
    molecular = {
        "stem_arm": "ACGTACGT",
        "product": "released_insert",
        "loop_words": ["AAA", "AAT"],
        "ends": {"left": "AGTC"},
    }
    reference = {
        "bundle_path": "preference/construction",
        "selection_path": "preference/selection.json",
    }
    permissions = {
        "context_id": "recorded/v1",
        "source_context_objective": "paired_scaffold_completions",
    }
    resolution = {
        "schema": "hop.resolved-design-request/v1",
        "intent": {**molecular, "prefer_preparation": reference},
        "permissions": permissions,
    }
    assert default_request(resolution) == {**molecular, "context": permissions}
    assert resolution["intent"]["prefer_preparation"] == reference


def test_explicit_reference_paths_reach_worker_as_authored(tmp_path, monkeypatch):
    from hop_design import construction

    authored = {
        "stem_arm": "ACGTACGT",
        "product": "released_insert",
        "context": "contexts/custom.json",
        "prefer_preparation": {
            "bundle_path": "prior/construction",
            "selection_path": "prior/selection.json",
        },
    }
    normalized = {
        **authored,
        "prefer_preparation": {
            "bundle_path": "preference/construction",
            "selection_path": "preference/selection.json",
        },
    }
    seen = []

    def resolve(request):
        seen.append(request)
        return SimpleNamespace(
            json_bytes=json.dumps(
                {
                    "schema": "hop.resolved-design-request/v1",
                    "intent": normalized,
                    "permissions": {"context_id": "inline/v1"},
                }
            ).encode()
        )

    monkeypatch.setattr(construction, "resolve_design_request", resolve)
    work = DiscoveryWork(tmp_path, worker=authored_request_worker)
    try:
        started = work.begin(authored, evaluations=1)
        wait_for(work, lambda status: status["status"] == "completed")
        actual = json.loads((Path(started["directory"]) / "authored-request.json").read_text())
        assert seen == [authored]
        assert actual == authored
    finally:
        work.close()


def test_family_or_staged_revision_request_rejects_before_start(tmp_path):
    work = DiscoveryWork(tmp_path, worker=zero_worker)
    try:
        for request in (
            {"stem_arm": "ACGN", "product": "hairpin"},
            {"schema": "hop.design-revision/v1"},
        ):
            with pytest.raises(ValueError):
                work.begin(request)
        assert work.snapshot() is None
        assert not list(tmp_path.iterdir())
    finally:
        work.close()


@pytest.mark.parametrize(
    "status,count",
    [("running", 1), ("stopping", 1), ("cancelled", None), ("completed", 0), ("failed", 1)],
)
def test_inspection_requires_a_finished_nonempty_snapshot(tmp_path, status, count):
    work = DiscoveryWork(tmp_path)
    work._job = {"id": "owned", "status": status, "matching_preparations": count}
    try:
        with pytest.raises(ValueError), work.inspectable_result("owned"):
            pytest.fail("An unfinished or empty result was exposed for inspection")
    finally:
        work.close()


def test_result_admission_reserves_owned_branch_and_releases_on_failure(tmp_path):
    work = DiscoveryWork(tmp_path)
    work._job = {
        "id": "owned",
        "status": "completed",
        "matching_preparations": 1,
        "directory": str(tmp_path / "discoveries" / "branch"),
        "can_continue": True,
    }
    try:
        with pytest.raises(ValueError, match="superseded"), work.inspectable_result("stale"):
            pytest.fail("A stale job was admitted")
        with (
            pytest.raises(RuntimeError, match="admission failed"),
            work.inspectable_result("owned") as directory,
        ):
            assert directory == tmp_path / "discoveries" / "branch"
            with pytest.raises(ValueError, match="being opened"):
                work.begin(None, previous="owned")
            with (
                pytest.raises(ValueError, match="being opened"),
                work.inspectable_result("owned"),
            ):
                pytest.fail("A duplicate admission was permitted")
            raise RuntimeError("admission failed")
        with work.inspectable_result("owned"):
            assert work.snapshot("owned")["status"] == "completed"
        work.close()
        with pytest.raises(ValueError, match="closed"), work.inspectable_result("owned"):
            pytest.fail("Closed work was admitted")
    finally:
        work.close()
