"""Continuation pages keep global candidate addresses and only new route attempts."""

import json

from hop_design import construction
from hop_design.design.construction.options.admission import captured_options
from hop_design.design.construction.options.explore import _explore_with_receipts
from hop_design.serialization import canonical_json_bytes
from tests.integration.test_scaffold_discovery import method_request
from tests.unit.test_construction_intent import STEM


def test_option_pages_equal_one_prefix_without_recompiling_previous_candidates(
    tmp_path, monkeypatch
):
    import hop_design.design.construction.options.explore as owner

    request = json.loads(method_request(tmp_path).read_text())["product"]
    path = tmp_path / "product.json"
    path.write_bytes(canonical_json_bytes(request))
    first, _ = _explore_with_receipts(path, max_continuations=1)
    first_path = first.write(tmp_path / "first")
    calls = []
    original = owner.evaluate_candidate

    def observed(*args, **kwargs):
        calls.append(kwargs["design_id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(owner, "evaluate_candidate", observed)
    second, _ = _explore_with_receipts(
        path,
        max_continuations=2,
        start_pair=1,
        local_source=first_path,
    )
    assert len(calls) == 2
    second_path = second.write(tmp_path / "second")
    assert not (second_path / "candidates/0000").exists()
    summary = json.loads(second.json_bytes)
    assert summary["pair_window"] == {"start": 1, "stop": 3}
    assert [c["ordinal"] for c in summary["candidates"]] == [1, 2]
    with captured_options(second_path) as (_, admitted, _, _):
        assert admitted == summary
    whole = construction.explore_construction_options(path, max_continuations=3)
    joined = json.loads(first.json_bytes)["options"] + summary["options"]
    assert joined == json.loads(whole.json_bytes)["options"]


def test_hairpin_continuation_keeps_only_new_candidates_and_old_selection(tmp_path):
    from hop_design.design.construction.packets.capture import write_snapshot
    from hop_design.design.construction.variants.source_capture import capture_exploration

    initial = construction.discover_designs(
        {"stem_arm": STEM, "product": "hairpin"},
        tmp_path / "discovery",
        max_evaluations=2,
    )
    selected = initial.sample(seed=0)
    before = initial.atlas(selected).json_bytes
    continued = initial.find_more(max_evaluations=1)
    page = tmp_path / "discovery/hairpin-snapshots/0001/scaffolds/branches/0000"
    assert not (page / "candidates/0000").exists()
    assert not (page / "candidates/0001").exists()
    assert (page / "candidates/0002").exists()
    assert continued.query()["coverage"]["evaluated_pairs"] == 3
    assert continued.atlas(selected).json_bytes == before
    reopened = construction.load_design_choices(tmp_path / "discovery")
    assert reopened.query() == continued.query()
    assert reopened.retrieve(selected, tmp_path / "materials").materialized_realization_ids == (
        selected["materialized_realization_id"],
    )
    # An explicit expansion captures a portable authority, including the prefix,
    # rather than the latest delta alone or the unmanifested discovery directory.
    _, files = capture_exploration(reopened._pool)
    write_snapshot(files, tmp_path / "portable")
    restored = construction.load_scaffold_exploration(tmp_path / "portable")
    assert restored.result_digest == reopened._pool.result_digest
    assert restored._options == reopened._pool._options
    assert restored._metadata == reopened._pool._metadata
    import pytest

    first_page = tmp_path / "discovery/hairpin-snapshots/0000"
    first_page.rename(tmp_path / "removed-page")
    with pytest.raises(ValueError, match="history"):
        construction.load_design_choices(tmp_path / "discovery")
    assert (
        construction.load_scaffold_exploration(tmp_path / "portable").result_digest
        == restored.result_digest
    )
