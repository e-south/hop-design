"""Replay preserves creation metadata without impersonating the executing runtime."""

import pytest

from hop_design.design import runtime as creation
from hop_design.design.runtime import producer_identity


def test_replay_origin_is_nested_scoped_and_does_not_change_runtime(monkeypatch):
    monkeypatch.setattr(creation, "version", lambda _name: "9.0.0")
    actual = producer_identity()
    assert creation.creation_version() == "9.0.0"
    with creation.replay_creation("0.1.0a10"):
        assert creation.creation_version() == "0.1.0a10"
        assert producer_identity() == actual
        with pytest.raises(RuntimeError), creation.replay_creation("0.1.0a9"):
            assert creation.creation_version() == "0.1.0a9"
            raise RuntimeError("interrupted replay")
        assert creation.creation_version() == "0.1.0a10"
    assert creation.creation_version() == "9.0.0"


@pytest.mark.parametrize("value", [None, "", " ", 1])
def test_invalid_creator_is_rejected(value):
    with pytest.raises(ValueError, match="creator"), creation.replay_creation(value):
        pass


def test_child_authority_scope_requires_an_admitted_creator_set(monkeypatch):
    monkeypatch.setattr(creation, "version", lambda _name: "current")
    with creation.replay_authority("older"):
        assert creation.creation_version() == "current"
    with creation.admitted_creators(("older", "current")):
        with creation.replay_authority("older"):
            assert creation.creation_version() == "older"
        assert creation.creation_version() == "current"
        with pytest.raises(ValueError, match="creator"), creation.replay_authority("unrecognized"):
            pass
    with creation.replay_authority("older"):
        assert creation.creation_version() == "current"
