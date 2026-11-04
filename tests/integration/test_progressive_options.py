"""Progressive execution retains the exact examined prefix and its failed attempts."""

import importlib
import json

import pytest

from tests.integration.test_construction_options import envelope


def test_first_choices_resume_matches_uninterrupted_prefix(tmp_path, monkeypatch):
    module = importlib.import_module("hop_design.design.construction.options.explore")
    path = envelope(tmp_path, "hairpin")
    original = module.evaluate_candidate
    attempts = []

    def observed(*args, **kwargs):
        attempts.append(kwargs["design_id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "evaluate_candidate", observed)
    first, _ = module._explore_with_receipts(path, max_continuations=4, first_choices=1)
    first.write(tmp_path / "first")
    start = json.loads(first.json_bytes)
    assert len(start["options"]) == 1
    assert start["candidates"][0]["status"] == "infeasible"
    assert start["coverage"]["evaluated_pairs"] == 2
    assert start["coverage"]["unexamined_pairs"] == 10
    assert len(attempts) == 2

    resumed, _ = module._explore_with_receipts(
        path, max_continuations=4, previous=tmp_path / "first"
    )
    assert len(attempts) == len(set(attempts)) == 4
    uninterrupted, _ = module._explore_with_receipts(path, max_continuations=4)
    assert resumed.json_bytes == uninterrupted.json_bytes
    assert dict(resumed._files) == dict(uninterrupted._files)
    # A saved snapshot remains independently readable after continuing elsewhere.
    assert (tmp_path / "first/summary.json").read_bytes() == first.json_bytes

    request = json.loads(path.read_text())
    request["foldback"]["geometry"]["loop_lengths_nt"] = [4]
    path.write_text(json.dumps(request))
    before = len(attempts)
    with pytest.raises(ValueError, match="same request"):
        module._explore_with_receipts(path, max_continuations=4, previous=tmp_path / "first")
    assert len(attempts) == before
