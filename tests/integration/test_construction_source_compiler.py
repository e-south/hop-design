"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_construction_source_compiler.py

Tests file-oriented compilation from construction source to portable authority.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import hop_design.construction as construction
from hop_design.design.construction import verification
from hop_design.design.construction.source import compile_construction_source
from hop_design.models.construction import ConstructionEndpoint, SearchCompletionStatus
from hop_design.models.construction.complete import (
    CompositionEnumerationPolicy,
    DerivedPrimerPolicy,
    DerivedSourceSsdnaPolicy,
    LinearSourceMaterializationSpec,
    MaterialResolutionMode,
    PcrPrimer,
    ReleaseSideRequirement,
    SourceDuplexPreparationPolicy,
    TypeIisReleaseRequest,
    WholeRouteConstraints,
)
from hop_design.models.construction.source import (
    ConstructionCompositionSource,
    ConstructionSource,
)
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import EndChemistry, StrandEnd
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes
from tests.contract.test_foldback_construction_discovery import (
    _nickase,
    _request,
    _terminus_enzyme,
)
from tests.integration.test_complete_construction_clone import (
    _clone_fixture,
    _provisioning,
    _type_iis,
)
from tests.integration.test_complete_construction_discovery import (
    _basal_result,
    _material,
    _verified_design,
)
from tests.integration.test_complete_construction_pcr import _foldback, _payload


def _materialization(
    *,
    adapter=None,
    forward_primer=None,
    reverse_primer=None,
    primer_annealing_length_nt: int | None = None,
) -> LinearSourceMaterializationSpec:
    return LinearSourceMaterializationSpec(
        source_preparation=SourceDuplexPreparationPolicy(
            source_ssdna=DerivedSourceSsdnaPolicy(
                mode=MaterialResolutionMode.DERIVE,
                five_prime_end=EndChemistry.HYDROXYL,
                three_prime_end=EndChemistry.HYDROXYL,
            ),
            forward_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=1,
            ),
            reverse_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=1,
            ),
        ),
        adapter=adapter,
        hairpin_pcr_forward_primer=(
            None
            if forward_primer is None
            else PcrPrimer(
                oligo=forward_primer,
                annealing_length_nt=(
                    primer_annealing_length_nt
                    if primer_annealing_length_nt is not None
                    else len(forward_primer.sequence_5prime)
                ),
            )
        ),
        hairpin_pcr_reverse_primer=(
            None
            if reverse_primer is None
            else PcrPrimer(
                oligo=reverse_primer,
                annealing_length_nt=(
                    primer_annealing_length_nt
                    if primer_annealing_length_nt is not None
                    else len(reverse_primer.sequence_5prime)
                ),
            )
        ),
    )


def _source(
    *,
    foldback,
    endpoint: ConstructionEndpoint,
    materialization: LinearSourceMaterializationSpec,
    basal=None,
    release: TypeIisReleaseRequest | None = None,
) -> ConstructionSource:
    return ConstructionSource(
        schema="hop.construction-source/v4",
        foldback=foldback,
        basal=basal,
        composition=ConstructionCompositionSource(
            endpoint=endpoint,
            materialization=materialization,
            release=release,
            whole_route_constraints=WholeRouteConstraints(),
            enumeration=CompositionEnumerationPolicy(
                max_combinations=10_000,
                max_realizations=10_000,
            ),
        ),
    )


def _write_source(path: Path, source: ConstructionSource) -> Path:
    path.write_text(
        yaml.safe_dump(source.model_dump(mode="json", by_alias=True), sort_keys=False),
        encoding="utf-8",
    )
    return path


def _local_receipt(path: Path, result):
    path.write_bytes(canonical_json_bytes(result))
    return construction.load_verified_local_neighborhood(path)


def _selected_inputs(tmp_path: Path, *, adapter_sequence: str | None = None):
    payload = _payload()
    design = _verified_design(tmp_path / "selected")
    foldback = _foldback(payload)
    basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    )
    encoding = design.plan.hairpin_encoding_insert.sequence
    adapter = next(
        item for item in basal.realizations[0].materials if item.material_id == "ligation-adapter"
    )
    source = _source(
        foldback=foldback.neighborhood.request,
        basal=basal.discovery.request,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        materialization=_materialization(
            adapter=_material(
                adapter.material_id,
                adapter.sequence_5prime if adapter_sequence is None else adapter_sequence,
            ),
            forward_primer=_material("forward-primer", encoding[:4]),
            reverse_primer=_material(
                "reverse-primer",
                reverse_complement_iupac(encoding[-4:]),
            ),
        ),
    )
    return design, foldback, basal, source


def test_file_source_compiles_direct_endpoint_from_separate_design_authority(
    tmp_path: Path,
) -> None:
    design = _verified_design(tmp_path / "direct")
    source = _source(
        foldback=_foldback(_payload()).neighborhood.request,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        materialization=_materialization(),
    )

    compilation = compile_construction_source(
        _write_source(tmp_path / "direct.yaml", source),
        design_bundle_path=tmp_path / "direct" / "design",
    )

    assert compilation.status == SearchCompletionStatus.COMPLETE.value
    assert compilation.endpoint == ConstructionEndpoint.SSDNA_HAIRPIN.value
    assert compilation.design_bundle_id == design.bundle.bundle_id


def test_file_source_compiles_pcr_and_clone_endpoints(tmp_path: Path) -> None:
    payload = _payload()
    pcr_design = _verified_design(tmp_path / "pcr")
    pcr_foldback = _foldback(payload)
    pcr_basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    )
    pcr_encoding = pcr_design.plan.hairpin_encoding_insert.sequence
    pcr_adapter = next(
        item
        for item in pcr_basal.realizations[0].materials
        if item.material_id == "ligation-adapter"
    )
    pcr_source = _source(
        foldback=pcr_foldback.neighborhood.request,
        basal=pcr_basal.discovery.request,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        materialization=_materialization(
            adapter=_material(pcr_adapter.material_id, pcr_adapter.sequence_5prime),
            forward_primer=_material("forward-primer", pcr_encoding[:4]),
            reverse_primer=_material("reverse-primer", reverse_complement_iupac(pcr_encoding[-4:])),
        ),
    )
    pcr = compile_construction_source(
        _write_source(tmp_path / "pcr.yaml", pcr_source),
        design_bundle_path=tmp_path / "pcr" / "design",
    )

    (
        clone_payload,
        clone_foldback,
        clone_basal,
        _,
        clone_adapter,
        complete_pcr_top,
        _,
    ) = _clone_fixture(tmp_path / "clone")
    clone_source = _source(
        foldback=clone_foldback.neighborhood.request,
        basal=clone_basal.discovery.request,
        endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
        materialization=_materialization(
            adapter=_material(clone_adapter.material_id, clone_adapter.sequence_5prime),
            forward_primer=_material("forward-primer", f"GGTCTC{complete_pcr_top[:4]}"),
            reverse_primer=_material(
                "reverse-primer",
                f"GGTCTC{reverse_complement_iupac(complete_pcr_top[-4:])}",
            ),
            primer_annealing_length_nt=4,
        ),
        release=TypeIisReleaseRequest(
            enzyme_provisioning=_provisioning(_type_iis(), max_operations=2),
            left=ReleaseSideRequirement(
                orientation=SiteOrientation.FORWARD,
                cohesive_end_sequence=complete_pcr_top[:4],
                overhang_end=StrandEnd.FIVE_PRIME,
            ),
            right=ReleaseSideRequirement(
                orientation=SiteOrientation.REVERSE,
                cohesive_end_sequence=reverse_complement_iupac(complete_pcr_top[-4:]),
                overhang_end=StrandEnd.FIVE_PRIME,
            ),
            max_site_pairs=16,
        ),
    )
    clone = compile_construction_source(
        _write_source(tmp_path / "clone.yaml", clone_source),
        design_bundle_path=tmp_path / "clone" / "design",
    )

    assert pcr.status == SearchCompletionStatus.COMPLETE.value
    assert pcr.endpoint == ConstructionEndpoint.HAIRPIN_PCR_DUPLEX.value
    assert pcr.bundle_id == "hop:construction-bundle/7c11ec382a8f/d570e91253a9bf8b"
    assert clone_payload == payload
    assert clone.status == SearchCompletionStatus.COMPLETE.value
    assert clone.endpoint == ConstructionEndpoint.CLONE_READY_DUPLEX.value


def test_file_source_compiles_exactly_one_selected_local_pair(tmp_path: Path) -> None:
    _, foldback, basal, source = _selected_inputs(tmp_path)

    compilation = construction.compile_construction_from_local_realizations(
        _write_source(tmp_path / "selected.yaml", source),
        design_bundle_path=tmp_path / "selected" / "design",
        foldback=_local_receipt(tmp_path / "foldback.json", foldback),
        foldback_realization_id=foldback.realizations[1].foldback_realization_id,
        basal=_local_receipt(tmp_path / "basal.json", basal),
        basal_realization_id=basal.realizations[0].basal_realization_id,
    )

    assert compilation.status == SearchCompletionStatus.COMPLETE.value
    assert compilation.nominal_combinations == 1
    assert compilation.examined_combinations == 1
    assert compilation.valid_realizations == 1
    output = compilation.write(tmp_path / "selected-construction")
    replayed = construction.load_verified_construction_bundle(output)
    assert replayed.bundle_id == compilation.bundle_id
    assert replayed.nominal_combinations == 1


def test_selected_pair_reuses_receipt_verification_without_discovery_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, foldback_result, basal_result, source = _selected_inputs(tmp_path)
    source_path = _write_source(tmp_path / "receipt-reuse.yaml", source)
    foldback = _local_receipt(tmp_path / "foldback.json", foldback_result)
    basal = _local_receipt(tmp_path / "basal.json", basal_result)
    arguments = {
        "design_bundle_path": tmp_path / "selected" / "design",
        "foldback": foldback,
        "foldback_realization_id": foldback_result.realizations[0].foldback_realization_id,
        "basal": basal,
        "basal_realization_id": basal_result.realizations[0].basal_realization_id,
    }
    expected = construction.compile_construction_from_local_realizations(
        source_path,
        **arguments,
    )

    def reject_replay(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("verified receipt was replayed during route compilation")

    monkeypatch.setattr(
        verification,
        "discover_foldback_neighborhood",
        reject_replay,
    )
    monkeypatch.setattr(
        verification,
        "discover_basal_neighborhood",
        reject_replay,
    )

    observed = construction.compile_construction_from_local_realizations(
        source_path,
        **arguments,
    )

    assert observed.bundle_id == expected.bundle_id
    assert observed.result_id == expected.result_id
    assert canonical_json_bytes(observed._verified_source().result) == canonical_json_bytes(
        expected._verified_source().result
    )


def test_selected_pair_rejects_an_unknown_realization_id(tmp_path: Path) -> None:
    _, foldback, basal, source = _selected_inputs(tmp_path)

    with pytest.raises(ValueError, match="selected foldback realization was not found"):
        construction.compile_construction_from_local_realizations(
            _write_source(tmp_path / "unknown.yaml", source),
            design_bundle_path=tmp_path / "selected" / "design",
            foldback=_local_receipt(tmp_path / "foldback.json", foldback),
            foldback_realization_id=f"hop:foldback-realization/{'a' * 64}@1",
            basal=_local_receipt(tmp_path / "basal.json", basal),
            basal_realization_id=basal.realizations[0].basal_realization_id,
        )


def test_selected_pair_rejects_an_unknown_basal_realization_id(tmp_path: Path) -> None:
    _, foldback, basal, source = _selected_inputs(tmp_path)

    with pytest.raises(ValueError, match="selected basal realization was not found"):
        construction.compile_construction_from_local_realizations(
            _write_source(tmp_path / "unknown-basal.yaml", source),
            design_bundle_path=tmp_path / "selected" / "design",
            foldback=_local_receipt(tmp_path / "foldback.json", foldback),
            foldback_realization_id=foldback.realizations[0].foldback_realization_id,
            basal=_local_receipt(tmp_path / "basal.json", basal),
            basal_realization_id=f"hop:basal-realization/{'a' * 64}@1",
        )


def test_selected_pair_requires_replay_verified_local_receipts(tmp_path: Path) -> None:
    _, foldback, basal, source = _selected_inputs(tmp_path)

    with pytest.raises(TypeError, match="replay-verified local receipts"):
        construction.compile_construction_from_local_realizations(
            _write_source(tmp_path / "raw-receipt.yaml", source),
            design_bundle_path=tmp_path / "selected" / "design",
            foldback=foldback,  # type: ignore[arg-type]
            foldback_realization_id=foldback.realizations[0].foldback_realization_id,
            basal=_local_receipt(tmp_path / "basal.json", basal),
            basal_realization_id=basal.realizations[0].basal_realization_id,
        )


def test_selected_pair_rejects_a_direct_construction_source(tmp_path: Path) -> None:
    _, foldback, basal, _ = _selected_inputs(tmp_path)
    source = _source(
        foldback=foldback.neighborhood.request,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        materialization=_materialization(),
    )

    with pytest.raises(ValueError, match="requires a PCR-bearing construction source"):
        construction.compile_construction_from_local_realizations(
            _write_source(tmp_path / "direct-selected.yaml", source),
            design_bundle_path=tmp_path / "selected" / "design",
            foldback=_local_receipt(tmp_path / "foldback.json", foldback),
            foldback_realization_id=foldback.realizations[0].foldback_realization_id,
            basal=_local_receipt(tmp_path / "basal.json", basal),
            basal_realization_id=basal.realizations[0].basal_realization_id,
        )


def test_selected_pair_rejects_local_receipts_with_reversed_families(tmp_path: Path) -> None:
    _, foldback, basal, source = _selected_inputs(tmp_path)

    with pytest.raises(ValueError, match="foldback receipt has the wrong local family"):
        construction.compile_construction_from_local_realizations(
            _write_source(tmp_path / "family.yaml", source),
            design_bundle_path=tmp_path / "selected" / "design",
            foldback=_local_receipt(tmp_path / "basal.json", basal),
            foldback_realization_id=foldback.realizations[0].foldback_realization_id,
            basal=_local_receipt(tmp_path / "foldback.json", foldback),
            basal_realization_id=basal.realizations[0].basal_realization_id,
        )


def test_selected_pair_rejects_a_basal_receipt_with_the_wrong_family(tmp_path: Path) -> None:
    _, foldback, basal, source = _selected_inputs(tmp_path)

    with pytest.raises(ValueError, match="basal receipt has the wrong local family"):
        construction.compile_construction_from_local_realizations(
            _write_source(tmp_path / "basal-family.yaml", source),
            design_bundle_path=tmp_path / "selected" / "design",
            foldback=_local_receipt(tmp_path / "foldback.json", foldback),
            foldback_realization_id=foldback.realizations[0].foldback_realization_id,
            basal=_local_receipt(tmp_path / "wrong-basal.json", foldback),
            basal_realization_id=basal.realizations[0].basal_realization_id,
        )


def test_selected_pair_rejects_a_receipt_from_another_source_request(tmp_path: Path) -> None:
    _, foldback, basal, source = _selected_inputs(tmp_path)
    enumeration = source.foldback.enumeration.model_copy(
        update={"max_search_nodes": source.foldback.enumeration.max_search_nodes + 1}
    )
    mismatched = source.model_copy(
        update={"foldback": source.foldback.model_copy(update={"enumeration": enumeration})}
    )

    with pytest.raises(ValueError, match="foldback receipt does not derive from the construction"):
        construction.compile_construction_from_local_realizations(
            _write_source(tmp_path / "mismatch.yaml", mismatched),
            design_bundle_path=tmp_path / "selected" / "design",
            foldback=_local_receipt(tmp_path / "foldback.json", foldback),
            foldback_realization_id=foldback.realizations[0].foldback_realization_id,
            basal=_local_receipt(tmp_path / "basal.json", basal),
            basal_realization_id=basal.realizations[0].basal_realization_id,
        )


def test_selected_pair_rejects_a_basal_receipt_from_another_source_request(
    tmp_path: Path,
) -> None:
    _, foldback, basal, source = _selected_inputs(tmp_path)
    assert source.basal is not None
    enumeration = source.basal.enumeration.model_copy(
        update={"max_search_nodes": source.basal.enumeration.max_search_nodes + 1}
    )
    mismatched = source.model_copy(
        update={"basal": source.basal.model_copy(update={"enumeration": enumeration})}
    )

    with pytest.raises(ValueError, match="basal receipt does not derive from the construction"):
        construction.compile_construction_from_local_realizations(
            _write_source(tmp_path / "basal-mismatch.yaml", mismatched),
            design_bundle_path=tmp_path / "selected" / "design",
            foldback=_local_receipt(tmp_path / "foldback.json", foldback),
            foldback_realization_id=foldback.realizations[0].foldback_realization_id,
            basal=_local_receipt(tmp_path / "basal.json", basal),
            basal_realization_id=basal.realizations[0].basal_realization_id,
        )


def test_selected_pair_returns_exact_infeasible_accounting(tmp_path: Path) -> None:
    _, foldback, basal, source = _selected_inputs(tmp_path, adapter_sequence="AAAA")

    compilation = construction.compile_construction_from_local_realizations(
        _write_source(tmp_path / "infeasible-pair.yaml", source),
        design_bundle_path=tmp_path / "selected" / "design",
        foldback=_local_receipt(tmp_path / "foldback.json", foldback),
        foldback_realization_id=foldback.realizations[0].foldback_realization_id,
        basal=_local_receipt(tmp_path / "basal.json", basal),
        basal_realization_id=basal.realizations[0].basal_realization_id,
    )

    assert compilation.status == SearchCompletionStatus.INFEASIBLE.value
    assert compilation.nominal_combinations == 1
    assert compilation.examined_combinations == 1
    assert compilation.valid_realizations == 0


def test_file_source_rejects_design_outside_the_authored_payload_space(
    tmp_path: Path,
) -> None:
    _verified_design(tmp_path / "mismatch", payload="GACT")
    source = _source(
        foldback=_foldback(_payload()).neighborhood.request,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        materialization=_materialization(),
    )

    with pytest.raises(ValueError, match="does not belong to the authored payload space"):
        compile_construction_source(
            _write_source(tmp_path / "mismatch.yaml", source),
            design_bundle_path=tmp_path / "mismatch" / "design",
        )


def test_file_source_rejects_a_forged_design_bundle(tmp_path: Path) -> None:
    _verified_design(tmp_path / "forged")
    source = _source(
        foldback=_foldback(_payload()).neighborhood.request,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        materialization=_materialization(),
    )
    design_path = tmp_path / "forged" / "design"
    plan_path = design_path / "hop-plan.json"
    plan_path.write_bytes(plan_path.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="artifact digest mismatch"):
        compile_construction_source(
            _write_source(tmp_path / "forged.yaml", source),
            design_bundle_path=design_path,
        )


def test_file_source_preserves_truncated_local_discovery(tmp_path: Path) -> None:
    _verified_design(tmp_path / "truncated")
    source = _source(
        foldback=_request(
            _nickase(),
            _terminus_enzyme(),
            max_search_nodes=1,
            max_realizations=100,
        ),
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        materialization=_materialization(),
    )

    compilation = compile_construction_source(
        _write_source(tmp_path / "truncated.yaml", source),
        design_bundle_path=tmp_path / "truncated" / "design",
    )

    assert compilation.status == SearchCompletionStatus.TRUNCATED.value


def test_file_source_preserves_infeasible_local_discovery(tmp_path: Path) -> None:
    _verified_design(tmp_path / "infeasible")
    source = _source(
        foldback=_request(_nickase(motif="ACATTTTGTG")),
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        materialization=_materialization(),
    )

    compilation = compile_construction_source(
        _write_source(tmp_path / "infeasible.yaml", source),
        design_bundle_path=tmp_path / "infeasible" / "design",
    )

    assert compilation.status == SearchCompletionStatus.INFEASIBLE.value


def test_file_source_rejects_unknown_schema_before_discovery(tmp_path: Path) -> None:
    _verified_design(tmp_path / "schema")
    path = tmp_path / "unsupported.yaml"
    document = _source(
        foldback=_foldback(_payload()).neighborhood.request,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        materialization=_materialization(),
    ).model_dump(mode="json", by_alias=True)
    document["schema"] = "hop.construction-source/v2"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported HOP construction source schema"):
        compile_construction_source(
            path,
            design_bundle_path=tmp_path / "schema" / "design",
        )
