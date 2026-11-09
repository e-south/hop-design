"""Fresh derivation runs once; external receipts and files still require replay."""

import pytest

from hop_design.design.construction.complete import discovery
from hop_design.design.construction.complete.bundle import (
    compile_construction_bundle,
    load_verified_construction_bundle,
)
from hop_design.design.construction.projections.complete import (
    project_complete_construction_summary,
)
from hop_design.serialization import canonical_json_bytes
from tests.integration.test_complete_construction_bundle import _verified_construction


@pytest.mark.parametrize("include_basal", [False, True])
def test_fresh_derivation_composes_once_and_external_receipts_replay(
    tmp_path, monkeypatch, include_basal
):
    original = discovery._discover_constructions_raw
    calls = []

    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(discovery, "_discover_constructions_raw", counted)
    source = _verified_construction(tmp_path, include_basal=include_basal)
    assert len(calls) == 1
    expected = canonical_json_bytes(source.result)
    assert project_complete_construction_summary(source).rows
    assert len(calls) == 1
    independently_admitted = discovery.VerifiedConstructionSpaceResult(
        result=source.result, foldback=source.foldback, basal=source.basal, design=source.design
    )
    assert len(calls) == 2
    assert canonical_json_bytes(independently_admitted.result) == expected
    compilation = compile_construction_bundle(source)
    assert len(calls) == 3
    published = compilation.write(tmp_path / "published")
    after_write = len(calls)
    assert after_write > 3
    loaded = load_verified_construction_bundle(published)
    assert len(calls) > after_write
    assert canonical_json_bytes(loaded._verified_source().result) == expected


def test_unregistered_container_cannot_inherit_an_admitted_results_authority(tmp_path):
    source = _verified_construction(tmp_path)
    forged = object.__new__(discovery.VerifiedConstructionSpaceResult)
    for name in ("result", "foldback", "basal", "design"):
        object.__setattr__(forged, name, getattr(source, name))
    with pytest.raises(ValueError, match="admitted composition"):
        project_complete_construction_summary(forged)


def test_mutating_a_derived_result_invalidates_its_admission(tmp_path):
    source = _verified_construction(tmp_path)
    object.__setattr__(
        source, "result", source.result.model_copy(update={"projection_inventory": ()})
    )
    with pytest.raises(ValueError, match="admitted composition"):
        project_complete_construction_summary(source)
