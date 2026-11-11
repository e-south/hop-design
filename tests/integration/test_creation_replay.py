"""Old authority bytes survive a newer creator version without skipping replay."""

from dataclasses import replace

import pytest

import hop_design as hop
from hop_design.design import runtime as creation
from hop_design.design.bundle import verify_hop_bundle_semantics
from hop_design.export.bundle import BundleIntegrityError
from hop_design.serialization import canonical_json_bytes


def test_design_replay_preserves_old_creator_but_new_designs_use_current_version(
    tmp_path, monkeypatch
):
    original = hop.compile(sequence="ACGT", design_id="creation-boundary")
    directory = original.write(tmp_path / "original")
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    creator = original.plan.lock.compiler_version
    monkeypatch.setattr(creation, "version", lambda _name: "9.0.0")
    fresh = hop.compile(sequence="ACGT", design_id="creation-boundary")
    assert fresh.plan.lock.compiler_version == "9.0.0"
    assert fresh.bundle.bundle_id != original.bundle.bundle_id
    # A result cannot authorize its own creator. A compatible checkpoint reader
    # will supply this scope only after admitting the recorded producer.
    with pytest.raises(BundleIntegrityError, match="replay"):
        hop.load_verified_bundle(directory)
    with creation.replay_creation(creator):
        loaded = hop.load_verified_bundle(directory)
    assert loaded.plan.lock.compiler_version == creator
    assert loaded.bundle == original.bundle
    assert dict(loaded.artifacts) == dict(original.artifacts)
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before
    with creation.replay_creation(creator):
        with pytest.raises(BundleIntegrityError, match="replay"):
            replace(loaded, plan=loaded.plan.model_copy(update={"payload_sequence": "AAAA"}))
        verify_hop_bundle_semantics(loaded)


def test_complete_preparation_replays_old_locals_and_materials(tmp_path, monkeypatch):
    from hop_design.design.construction.complete import bundle as bundles
    from hop_design.design.construction.verification import (
        verify_basal_neighborhood_result,
        verify_foldback_neighborhood_result,
    )
    from hop_design.models.construction import ConstructionEndpoint
    from tests.integration.test_complete_construction_projections import _verified_result

    original = _verified_result(tmp_path / "source", ConstructionEndpoint.CLONE_READY_DUPLEX)
    compilation = bundles.compile_construction_bundle(original)
    output = compilation.write(tmp_path / "construction")
    monkeypatch.setattr(creation, "version", lambda _name: "9.0.0")
    with creation.replay_creation(original.result.provenance.hop_version):
        loaded = bundles.load_verified_construction_bundle(output)
    assert loaded.result_id == original.result.result_id
    assert canonical_json_bytes(loaded._verified_source().result) == canonical_json_bytes(
        original.result
    )
    assert dict(loaded._artifacts) == dict(compilation._artifacts)
    # Embedded authorities must agree with the admitted creator too; the
    # reader does not replace that binding with their self-reported labels.
    with creation.replay_creation(original.result.provenance.hop_version):
        verify_foldback_neighborhood_result(original.foldback.result)
        verify_basal_neighborhood_result(original.basal.result)
    assert creation.creation_version() == "9.0.0"


def test_method_bundle_replays_old_creator_and_exact_exports(tmp_path, monkeypatch):
    import hop_design.methods as methods
    from tests.support.linear_source_method import linear_source_method_request

    compilation = methods.compile_linear_source_method_bundle(linear_source_method_request())
    output = compilation.write(tmp_path / "method")
    monkeypatch.setattr(creation, "version", lambda _name: "9.0.0")
    with creation.replay_creation(compilation.bundle.compiler_version):
        loaded = methods.load_verified_method_bundle(output)
    assert loaded.bundle == compilation.bundle
    assert loaded.plan == compilation.result.plan
    assert dict(loaded.artifacts) == dict(compilation.artifacts)


@pytest.mark.parametrize("region", ["basal", "foldback"])
def test_sequence_space_replay_preserves_the_declared_creator(region, monkeypatch):
    if region == "basal":
        from hop_design.design.construction import basal_space as space
        from tests.contract.test_basal_sequence_space import canonical_request, compact_request

        request = compact_request(canonical_request())
    else:
        from hop_design.design.construction import foldback_space as space
        from tests.contract.test_foldback_population_discovery import _space_request

        request = _space_request()
    original = space.discover_sequence_space(request)
    before = canonical_json_bytes(original)
    monkeypatch.setattr(creation, "version", lambda _name: "9.0.0")
    with creation.replay_creation(original.hop_version):
        assert canonical_json_bytes(space.verify_sequence_space(original)) == before
    assert space.discover_sequence_space(request).hop_version == "9.0.0"


@pytest.mark.parametrize("region", ["foldback", "basal"])
def test_local_replay_proof_cannot_cross_creator_bindings(tmp_path, monkeypatch, region):
    from hop_design.design.construction import verification
    from hop_design.models.construction import ConstructionEndpoint
    from tests.integration.test_complete_construction_projections import _verified_result

    original = _verified_result(tmp_path / "source", ConstructionEndpoint.CLONE_READY_DUPLEX)
    result = getattr(original, region).result
    verify = getattr(verification, f"verify_{region}_neighborhood_result")
    monkeypatch.setattr(creation, "version", lambda _name: "9.0.0")
    with verification.local_replay_scope():
        with creation.replay_creation(original.result.provenance.hop_version):
            verify(result)
        # The executor and body are identical. Only the admitted creator has
        # changed, so a proof of the first binding cannot admit the second.
        with pytest.raises(verification.ConstructionVerificationError, match="replay"):
            verify(result)
