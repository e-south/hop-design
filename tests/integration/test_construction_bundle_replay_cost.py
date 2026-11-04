"""Keep full admission at file boundaries without replaying again for a handoff."""

import json

import pytest

from hop_design import construction
from hop_design.design.construction.complete import bundle as bundles
from hop_design.models.construction import ConstructionEndpoint
from tests.integration.test_complete_construction_projections import _verified_result
from tests.integration.test_request_execution import hairpin_request, request_path


@pytest.mark.parametrize("author_request", [request_path, hairpin_request])
def test_options_share_local_proofs_only_during_one_evaluation(
    tmp_path, monkeypatch, author_request
):
    from collections import Counter
    from contextlib import nullcontext

    from hop_design.design.construction import verification
    from hop_design.serialization import canonical_json_bytes

    calls = []
    for name in ("discover_foldback_neighborhood", "discover_basal_neighborhood"):
        original = getattr(verification, name)

        def observed(request, *, discover=original, family=name):
            calls.append((family, canonical_json_bytes(request)))
            return discover(request)

        monkeypatch.setattr(verification, name, observed)

    path = author_request(tmp_path)
    first = construction.explore_construction_options(path, max_continuations=1)
    counts = Counter(calls)
    assert counts and set(counts.values()) == {1}
    assert verification._proofs.get() is None
    calls.clear()
    second = construction.explore_construction_options(path, max_continuations=1)
    assert Counter(calls) == counts
    assert second._files == first._files
    assert verification._proofs.get() is None
    # Independent full replays are the byte-for-byte oracle, under the same
    # producer. The optimization must not change outcomes or any exported file.
    monkeypatch.setattr(
        "hop_design.design.construction.options.explore.local_replay_scope", nullcontext
    )
    replayed = construction.explore_construction_options(path, max_continuations=1)
    assert replayed._files == first._files


def test_loading_a_bundle_performs_one_whole_route_replay(tmp_path, monkeypatch):
    source = _verified_result(tmp_path / "source", ConstructionEndpoint.CLONE_READY_DUPLEX)
    path = bundles.compile_construction_bundle(source).write(tmp_path / "bundle")
    original = bundles.verify_construction_space_result
    calls = []

    def observed(*args, **kwargs):
        calls.append(None)
        return original(*args, **kwargs)

    monkeypatch.setattr(bundles, "verify_construction_space_result", observed)
    loaded = bundles.load_verified_construction_bundle(path)
    assert loaded.result_id == source.result.result_id
    assert len(calls) == 1


@pytest.mark.parametrize("author_request", [request_path, hairpin_request])
def test_execution_reuses_compilation_after_verified_write(tmp_path, monkeypatch, author_request):
    original = bundles.load_verified_construction_bundle
    loads = []

    def observed(*args, **kwargs):
        loads.append(args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(bundles, "load_verified_construction_bundle", observed)
    execution = construction.execute_construction_request(
        author_request(tmp_path), design_id="receipt-reuse", continuation="sole-witness"
    )
    # Publication still fully admits its staged bytes. Handoff reads the
    # immutable compilation that was already replayed, not its published path.
    assert len(loads) == 1
    output = execution.write(tmp_path / "execution")
    for expected_count in (2, 3):
        loaded = construction.load_verified_construction_bundle(output / "construction")
        assert len(loads) == expected_count
        assert loaded.result_id == json.loads(execution.json_bytes)["result_id"]
        assert loaded.status == "complete"
    artifact = output / "construction/construction-result.json"
    artifact.write_bytes(artifact.read_bytes() + b"\n")
    with pytest.raises(ValueError, match=r"(size|digest) mismatch"):
        construction.load_verified_construction_bundle(output / "construction")


def test_execution_requires_successful_write_admission_before_handoff(tmp_path, monkeypatch):
    from hop_design.design.construction import request_execution

    compile_original = request_execution.compile_request_candidate

    def corrupt_packaging(*args, **kwargs):
        receipt = compile_original(*args, **kwargs)
        artifacts = dict(receipt._artifacts)
        artifacts["construction-result.json"] = b"{}\n"
        return type(receipt)._create(
            construction=receipt._construction, bundle=receipt._bundle, artifacts=artifacts
        )

    def unexpected_handoff(*args, **kwargs):
        raise AssertionError("A failed publication must not produce an outcome or handoff.")

    monkeypatch.setattr(request_execution, "compile_request_candidate", corrupt_packaging)
    monkeypatch.setattr(request_execution, "describe_complete_outcome", unexpected_handoff)
    with pytest.raises(ValueError, match="artifact digest mismatch"):
        construction.execute_construction_request(
            request_path(tmp_path), design_id="bad-packaging", continuation="sole-witness"
        )


@pytest.mark.parametrize("author_request", [request_path, hairpin_request])
def test_source_packages_its_fresh_replay_without_repeating_it(
    tmp_path, monkeypatch, author_request
):
    original = bundles.verify_construction_space_result
    replays = []

    def observed(*args, **kwargs):
        replays.append(None)
        return original(*args, **kwargs)

    monkeypatch.setattr(bundles, "verify_construction_space_result", observed)
    execution = construction.execute_construction_request(
        author_request(tmp_path), design_id="fresh-replay", continuation="sole-witness"
    )
    assert json.loads(execution.json_bytes)["status"] == "complete"
    # Discovery owns its replay; packaging does not repeat it. Publication
    # still independently replays the actual staged files exactly once.
    assert len(replays) == 1


def test_discovery_projects_branch_receipts_without_reopening_candidates(tmp_path, monkeypatch):
    from tests.integration.test_scaffold_discovery import method_request

    path = method_request(tmp_path)
    request = json.loads(path.read_bytes())
    request["max_continuations_per_branch"] = 1
    path.write_text(json.dumps(request))
    original = bundles.load_verified_construction_bundle
    loads = []

    def observed(*args, **kwargs):
        loads.append(args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(bundles, "load_verified_construction_bundle", observed)
    packet = construction.discover_scaffolds(path)
    result = json.loads(packet.json_bytes)
    assert [b["complete_preparations"] for b in result["branches"]] == [1, 1, 0]
    assert len(result["branches"][2]["failures"]) == 1
    # Each candidate fully admits its staged publication once. The invocation
    # then checks published bytes against that proof, without a second replay.
    assert len(loads) == 3
    output = packet.write(tmp_path / "discovery")
    for expected_count in (6, 9):
        pool = construction.load_scaffold_exploration(output)
        assert len(json.loads(pool.json_bytes)["options"]) == 2
        assert len(loads) == expected_count


def test_candidate_reuse_still_checks_the_actual_published_files(tmp_path, monkeypatch):
    from hop_design.design.construction.request_execution import ConstructionRequestExecution

    original = ConstructionRequestExecution.write

    def corrupt_after_publication(self, destination):
        output = original(self, destination)
        path = output / "construction/construction-result.json"
        path.write_bytes(path.read_bytes() + b"\n")
        return output

    monkeypatch.setattr(ConstructionRequestExecution, "write", corrupt_after_publication)
    with pytest.raises(ValueError, match=r"(size|digest) mismatch"):
        construction.explore_construction_options(hairpin_request(tmp_path), max_continuations=1)
