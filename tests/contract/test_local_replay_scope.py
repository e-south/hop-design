"""Admission reuse preserves exact proof inputs, failure checks and scope lifetime."""

from unittest.mock import patch

import pytest

from hop_design.design.construction import verification
from tests.contract.test_foldback_construction_discovery import _nickase, _request


def test_identical_proofs_reuse_only_within_one_admission():
    result = verification.discover_foldback_neighborhood(_request(_nickase(), max_search_nodes=1))
    original = verification.discover_foldback_neighborhood
    with patch.object(verification, "discover_foldback_neighborhood", wraps=original) as replay:
        with verification.local_replay_scope():
            first = verification.verify_foldback_neighborhood_result(result)
            second = verification.verify_foldback_neighborhood_result(result)
            assert first.result == second.result == result
            assert replay.call_count == 1
            changed = result.model_copy(update={"result_id": result.result_id + "-bad"})
            with pytest.raises(ValueError):
                verification.verify_foldback_neighborhood_result(changed)
            with patch.object(
                verification, "producer_identity", return_value={"implementation": "changed"}
            ):
                verification.verify_foldback_neighborhood_result(result)
            assert replay.call_count >= 2
        before = replay.call_count
        verification.verify_foldback_neighborhood_result(result)
        assert replay.call_count == before + 1
    assert first._verified_result() == result


def test_proof_scope_restores_parent_and_releases_failed_invocations():
    with verification.local_replay_scope():
        parent = verification._proofs.get()
        verification._remember((b"parent", b"proof"))
        with pytest.raises(RuntimeError, match="interrupted"), verification.local_replay_scope():
            verification._remember((b"child", b"proof"))
            assert verification._proofs.get() == {(b"child", b"proof")}
            raise RuntimeError("interrupted")
        assert verification._proofs.get() is parent
        assert parent == {(b"parent", b"proof")}
    assert verification._proofs.get() is None


def test_local_proofs_respect_entry_and_byte_limits():
    with verification.local_replay_scope():
        for index in range(100):
            verification._remember((str(index).encode(), b"proof"))
        assert len(verification._proofs.get()) == 64
    with verification.local_replay_scope():
        verification._remember((b"large", b"x" * 8_388_608))
        assert verification._proofs.get() == set()
        verification._remember((b"small", b"proof"))
        assert verification._proofs.get() == {(b"small", b"proof")}


def test_a_failed_replay_does_not_seed_a_proof():
    result = verification.discover_foldback_neighborhood(_request(_nickase(), max_search_nodes=1))
    original = verification.discover_foldback_neighborhood
    with verification.local_replay_scope():
        with (
            patch.object(
                verification,
                "discover_foldback_neighborhood",
                side_effect=ValueError("interrupted"),
            ),
            pytest.raises(ValueError, match="interrupted"),
        ):
            verification.verify_foldback_neighborhood_result(result)
        assert verification._proofs.get() == set()
        with patch.object(verification, "discover_foldback_neighborhood", wraps=original) as replay:
            verification.verify_foldback_neighborhood_result(result)
            assert replay.call_count == 1
