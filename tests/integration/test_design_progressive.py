"""A first-choice stop remains resumable through the same public lifecycle."""

import importlib
import json

import pytest

from hop_design import construction
from tests.unit.test_construction_intent import STEM


@pytest.mark.parametrize("product", ["hairpin", "adapter_ligated_hairpin"])
def test_first_hairpin_choices_resume_without_recompiling_prior_attempts(
    product, tmp_path, monkeypatch
):
    module = importlib.import_module("hop_design.design.construction.options.explore")
    original = module.evaluate_candidate
    attempts = []

    def observed(*args, **kwargs):
        attempts.append(kwargs["design_id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "evaluate_candidate", observed)
    request = {"stem_arm": STEM, "product": product}
    first = construction.discover_designs(
        request, tmp_path / "progressive", max_evaluations=4, first_choices=1
    )
    initial = first.query()
    assert initial["matching_preparations"] == 1
    assert initial["execution"]["max_evaluations"] == 4
    assert initial["execution"]["first_choices"] == 1
    assert initial["coverage"]["evaluated_pairs"] == 2
    assert initial["coverage"]["unexamined_pairs"] > 0
    assert "continue_search" in first.explain()["actions"]
    selected = first.sample(seed=0)
    before = len(attempts)
    continued = first.find_more(max_evaluations=2)
    assert len(attempts) == before + 2
    assert len(attempts) == len(set(attempts)) == 4
    whole = construction.discover_designs(request, tmp_path / "whole", max_evaluations=4)
    assert continued.query()["paths"] == whole.query()["paths"]
    assert continued.query()["coverage"] == whole.query()["coverage"]
    assert first.query() == initial
    loaded = construction.load_design_choices(tmp_path / "progressive")
    assert loaded.query() == continued.query()
    # The discovery's history resolves an explicit old selection to its saved
    # snapshot, rather than silently binding it to the newest pool.
    receipt = loaded.retrieve(selected, tmp_path / "old-selection")
    assert receipt.materialized_realization_ids == (selected["materialized_realization_id"],)
    assert json.loads(loaded.atlas(selected).json_bytes)["atlas"]["states"]
    foreign = {**selected, "snapshot_digest": "sha256:" + "0" * 64}
    with pytest.raises(ValueError, match="snapshot"):
        loaded.retrieve(foreign, tmp_path / "foreign")


def test_interruption_before_snapshot_publication_can_resume_from_saved_intent(
    tmp_path, monkeypatch
):
    from hop_design.design.construction.intents.hairpin_history import HairpinSnapshot

    original = HairpinSnapshot.write

    def interrupted(*args, **kwargs):
        raise OSError("interrupted before publication")

    monkeypatch.setattr(HairpinSnapshot, "write", interrupted)
    directory = tmp_path / "interrupted"
    with pytest.raises(OSError, match="interrupted"):
        construction.discover_designs(
            {"stem_arm": STEM, "product": "hairpin"}, directory, max_evaluations=1
        )
    assert (directory / "intent/request.json").is_file()
    assert not (directory / "hairpin-snapshots/0000").exists()
    monkeypatch.setattr(HairpinSnapshot, "write", original)
    resumed = construction.continue_design_discovery(directory, max_evaluations=2)
    assert resumed.query()["coverage"]["evaluated_pairs"] == 2
    assert resumed.query()["matching_preparations"] == 1
    summary = json.loads((resumed.inspection_source / "branches/0000/summary.json").read_bytes())
    assert [c["status"] for c in summary["candidates"]] == ["infeasible", "complete"]
