"""Creator-bound evidence remains usable after admission by a newer executor."""

import json

import pytest

from hop_design import construction
from hop_design.design import runtime as creation
from hop_design.design.construction.surveys.admission import open_survey
from hop_design.design.construction.surveys.execute import load_request
from hop_design.design.construction.surveys.navigation import history
from hop_design.design.construction.surveys.retrieve import retrieve_admitted_witness
from hop_design.design.runtime import producer_identity
from hop_design.models.construction.product_request import ProductRequest
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.integration.test_survey_plane_pruning import execute, request_file
from tests.support.interface_surveys import indexed_survey, survey_selection


def test_admitted_old_proof_replays_against_its_creator_not_current_executor(tmp_path, monkeypatch):
    path = request_file(tmp_path)
    checkpoint = tmp_path / "source.sqlite"
    original = producer_identity()
    first = execute(path, checkpoint, 1)
    assert first["coverage"]["excluded_pairs"] == 1
    assert first["coverage"]["unexamined_pairs"] == 1
    before = checkpoint.read_bytes()
    executor = {**original, "package_version": "9.0.0", "package_content": "sha256:" + "b" * 64}
    monkeypatch.setattr(history, "producer_identity", lambda: executor)
    # Explicitly admit the original binding. This is the migration's private
    # reader seam, not permission for an arbitrary new producer to resume.
    saved, limits = open_survey(checkpoint, request=load_request(path), producer=original)
    with saved:
        proofs = history.EmptyPlaneHistory(saved, limits)
        assert proofs.producer == executor
        for target, _step, raw, _count, _exhausted in saved.evaluations():
            for digest in history.proof_references(json.loads(raw)):
                proofs.restore(target, digest)
        assert proofs.coverage()["certified_empty_planes"] == 1
    with pytest.raises(ValueError, match="producer"):
        open_survey(checkpoint, request=load_request(path), producer=executor)
    assert checkpoint.read_bytes() == before


@pytest.mark.parametrize("region", ["foldback", "basal"])
def test_admitted_old_local_cache_keeps_exact_creator_binding(tmp_path, monkeypatch, region):
    from hop_design.design.construction.surveys.admission.locals import LocalReceipts

    path, checkpoint = indexed_survey(tmp_path)
    saved, limits = open_survey(
        checkpoint, request=load_request(path), producer=producer_identity()
    )
    with saved:
        record = json.loads(saved.record(0, step=0))
        product = ProductRequest.model_validate_json(saved.get_object(record["product_request"]))
        local = getattr(product.construction_source(), region)
        original = saved.cached(sha256_digest(canonical_json_bytes(local)))
        assert original is not None
        monkeypatch.setattr(creation, "version", lambda _name: "9.0.0")
        assert LocalReceipts(saved, limits).get(local).json_bytes == original


def test_old_survey_selection_keeps_exact_handoff_under_new_creation_version(tmp_path, monkeypatch):
    path, checkpoint = indexed_survey(tmp_path)
    selection = survey_selection(path, checkpoint, target=0, step=0)
    construction.retrieve_interface_survey_witness(
        path, checkpoint, selection=selection, destination=tmp_path / "before"
    )
    source_producer = producer_identity()
    before = checkpoint.read_bytes()
    monkeypatch.setattr(creation, "version", lambda _name: "9.0.0")
    saved, limits = open_survey(checkpoint, request=load_request(path), producer=source_producer)
    with saved:
        receipt = retrieve_admitted_witness(
            saved, limits, selection=selection, destination=tmp_path / "after"
        )
    assert selection["materialized_realization_id"] in receipt.materialized_realization_ids

    def relative(root):
        return {
            p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()
        }

    assert relative(tmp_path / "after") == relative(tmp_path / "before")
    assert checkpoint.read_bytes() == before
