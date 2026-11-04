"""Isolated inspection preserves exact output and the captured authority boundary."""

import copy
import json
from dataclasses import replace

import pytest

from hop_design.api import _InspectionProjection
from hop_design.commands.design.inspection_hover import HoverCache
from hop_design.commands.design.inspection_worker import SingleWorker
from tests.integration.test_atlas_edition import captured_choices as captured_choices


def test_isolated_preview_matches_shared_renderer_and_rejects_bad_authority(
    captured_choices, tmp_path, monkeypatch
):
    edition = captured_choices.freeze(tmp_path / "edition", compact=True)
    answer = edition.query()
    identity = answer["paths"][0]["materialized_realization_id"]
    expected = _InspectionProjection.preview(edition, identity, answer)

    def forbidden(*args, **kwargs):
        pytest.fail("An isolated preview must not query or select the cohort again")

    monkeypatch.setattr(edition, "query", forbidden)
    monkeypatch.setattr(edition, "select", forbidden)
    job = _InspectionProjection.preview_job(edition, identity, answer)
    worker = SingleWorker(_InspectionProjection.render_preview_job)
    try:
        assert worker.call(job) == expected
        with pytest.raises(ValueError, match="MolecularDescriptor"):
            worker.call(replace(job, descriptor=b"{}"))
        wrong_descriptor = json.loads(job.descriptor)
        wrong_descriptor["stem"] = "AAAA"
        with pytest.raises(ValueError, match="descriptor disagrees"):
            worker.call(replace(job, descriptor=json.dumps(wrong_descriptor).encode()))
        assert worker.call(job) == expected
    finally:
        worker.close()
    with pytest.raises(ValueError, match="recorded pool"):
        _InspectionProjection.preview_job(edition, "missing", answer)
    wrong = copy.deepcopy(answer)
    wrong["snapshot_digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="snapshot"):
        _InspectionProjection.preview_job(edition, identity, wrong)
    archive = edition._directory / edition._prefix(identity) / "evidence.zip"
    raw = archive.read_bytes()
    archive.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(ValueError, match="digest"):
        _InspectionProjection.preview_job(edition, identity, answer)


def test_hover_cache_uses_isolation_for_compact_editions(captured_choices, tmp_path, monkeypatch):
    edition = captured_choices.freeze(tmp_path / "edition", compact=True)
    answer = edition.query()
    identity = answer["paths"][0]["materialized_realization_id"]
    expected, _ = _InspectionProjection.preview(edition, identity, answer)

    def forbidden(*args, **kwargs):
        pytest.fail("Compact hover must not validate and render in the cohort process")

    monkeypatch.setattr(_InspectionProjection, "preview", forbidden)
    cache = HoverCache(tmp_path)
    try:
        result = cache.get(edition, identity, answer["query"], answer=answer)
        assert (tmp_path / result["molecule"].removeprefix("/files/")).read_bytes() == expected
    finally:
        cache.close()
    assert not cache.root.exists()


def test_visible_route_and_hairpin_share_one_admission(captured_choices, tmp_path, monkeypatch):
    from hop_design.design.construction.editions import preview_job as module

    edition = captured_choices.freeze(tmp_path / "edition", compact=True)
    answer = edition.query()
    identity = answer["paths"][0]["materialized_realization_id"]
    phases = ("duplex", "cleaved_duplex", "annealed_complex")
    expected = _InspectionProjection.preview(edition, identity, answer)
    drawings, scenes = _InspectionProjection.scenes(
        edition, identity, answer, phases=phases, render_policy="current"
    )
    calls = []
    check = module.check_descriptor

    def counted(*args):
        calls.append(True)
        return check(*args)

    monkeypatch.setattr(module, "check_descriptor", counted)
    job = module.preview_job(edition, identity, answer, phases=phases)
    overview, summary = module.render_preview_job(job)
    assert calls == [True]
    assert overview == expected[0]
    assert summary.pop("route_drawings") == drawings
    assert summary.pop("route_scenes") == scenes
    assert summary == expected[1]
    with pytest.raises(ValueError, match="MolecularDescriptor"):
        module.render_preview_job(replace(job, descriptor=b"{}"))
    with pytest.raises(ValueError, match="distinct recorded"):
        module.preview_job(edition, identity, answer, phases=("duplex", "duplex"))
