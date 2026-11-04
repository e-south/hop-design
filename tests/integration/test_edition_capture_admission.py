"""Capturing several preparations admits one immutable survey snapshot."""

import shutil
import sqlite3

import pytest

from hop_design import construction
from hop_design.design.construction.surveys.index import SurveyIndex
from tests.integration.test_design_discovery import intent_document


@pytest.fixture(scope="module")
def capture_pool(tmp_path_factory):
    intent = intent_document()
    intent["ends"] = {"left": "AGTC", "right": "AGTC"}
    foldback = intent["context"]["foldback"]
    foldback["geometry"].update(annealing_arm_lengths_bp=[9], loop_sequences=["GAAA", "TTTC"])
    foldback["max_retained_overhead_nt"] = 32
    choices = construction.discover_designs(
        intent, tmp_path_factory.mktemp("capture-admission") / "choices", max_evaluations=4
    )
    assert len(choices.query()["paths"]) >= 2
    return choices


def test_capture_admits_once_and_retains_exact_member_handoffs(capture_pool, tmp_path, monkeypatch):
    paths = capture_pool.query()["paths"]
    expected = {}
    for number, path in enumerate(paths):
        destination = tmp_path / f"expected-{number}"
        capture_pool.retrieve(capture_pool.select(path), destination)
        expected[path["materialized_realization_id"]] = {
            p.relative_to(destination): p.read_bytes()
            for p in destination.rglob("*")
            if p.is_file()
        }
    admitted = []
    validate = SurveyIndex._validate

    def checked(index):
        admitted.append(index)
        return validate(index)

    monkeypatch.setattr(SurveyIndex, "_validate", checked)
    edition = capture_pool.freeze(tmp_path / "edition", compact=True)
    assert len(admitted) == 1, "Capture must not revalidate the entire survey for each preparation"
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        admitted[0]._db.execute("SELECT 1")
    for number, (identity, files) in enumerate(expected.items()):
        destination = tmp_path / f"actual-{number}"
        edition.retrieve(edition.select(identity), destination)
        assert {
            p.relative_to(destination): p.read_bytes()
            for p in destination.rglob("*")
            if p.is_file()
        } == files


def test_capture_closes_admission_on_member_failure(capture_pool, tmp_path, monkeypatch):
    from hop_design.design.construction.surveys import retrieve

    recovered = []
    recover = retrieve.recover_witness

    def fail_second(index, *args, **kwargs):
        recovered.append(index)
        if len(recovered) == 2:
            raise RuntimeError("injected member failure")
        return recover(index, *args, **kwargs)

    monkeypatch.setattr(retrieve, "recover_witness", fail_second)
    with pytest.raises(RuntimeError, match="injected member failure"):
        capture_pool.freeze(tmp_path / "edition", compact=True)
    assert len(recovered) == 2 and recovered[0] is recovered[1]
    assert not (tmp_path / "edition").exists()
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        recovered[0]._db.execute("SELECT 1")


def test_capture_revalidates_changed_checkpoint_before_export(capture_pool, tmp_path):
    root = tmp_path / "changed"
    shutil.copytree(capture_pool._directory, root)
    choices = construction.load_design_choices(root)
    with sqlite3.connect(root / "survey.sqlite") as db:
        digest, raw = db.execute("SELECT digest, content FROM objects LIMIT 1").fetchone()
        db.execute(
            "UPDATE objects SET content=? WHERE digest=?", (raw[:-1] + bytes([raw[-1] ^ 1]), digest)
        )
    with pytest.raises(ValueError):
        choices.freeze(tmp_path / "edition", compact=True)
    assert not (tmp_path / "edition").exists()


def test_capture_keeps_preservation_report_and_selection(capture_pool, tmp_path):
    baseline = capture_pool.sample(seed=1)
    query = capture_pool.preserve(baseline, stage="hairpin", except_neighborhood="loop")
    path = next(path for path in capture_pool.query(query)["paths"] if path["matches"])
    selected = capture_pool.select(path, query=query)
    expected = tmp_path / "expected"
    capture_pool.retrieve(selected, expected)
    edition = capture_pool.freeze(tmp_path / "edition", compact=True, query=query)
    actual = tmp_path / "actual"
    edition.retrieve(edition.select(selected["materialized_realization_id"]), actual)
    assert {p.relative_to(actual): p.read_bytes() for p in actual.rglob("*") if p.is_file()} == {
        p.relative_to(expected): p.read_bytes() for p in expected.rglob("*") if p.is_file()
    }
