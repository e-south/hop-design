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
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.source import compile_construction_source
from hop_design.models.construction import (
    ConstructionEndpoint,
    FoldbackTarget,
    SearchCompletionStatus,
)
from hop_design.models.construction.complete import (
    CompositionEnumerationPolicy,
    DerivedPrimerPolicy,
    DerivedSourceSsdnaPolicy,
    EndpointAuxiliaryPolicy,
    FixedAdapterPolicy,
    FixedEndpointPrimerPolicy,
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
from hop_design.models.coordinates import Boundary
from hop_design.models.enzymes import RecognitionOrientationSemantics
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import EndChemistry, StrandEnd
from hop_design.models.payload import ExactPayload
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes
from tests.contract.test_complete_source_partition_replay import PAYLOAD
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
from tests.support.source_partition import source_partition_for_route


def _materialization(
    *,
    adapter=None,
    forward_primer=None,
    reverse_primer=None,
    primer_annealing_length_nt: int | None = None,
) -> LinearSourceMaterializationSpec:
    endpoint_auxiliaries = None
    if any(item is not None for item in (adapter, forward_primer, reverse_primer)):
        if adapter is None or forward_primer is None or reverse_primer is None:
            raise ValueError("Exact test auxiliary inputs must be complete.")
        annealing_length = (
            primer_annealing_length_nt
            if primer_annealing_length_nt is not None
            else len(forward_primer.sequence_5prime)
        )
        endpoint_auxiliaries = EndpointAuxiliaryPolicy(
            adapter=FixedAdapterPolicy(
                mode=MaterialResolutionMode.FIXED,
                material=adapter,
            ),
            forward_primer=FixedEndpointPrimerPolicy(
                mode=MaterialResolutionMode.FIXED,
                primer=PcrPrimer(
                    oligo=forward_primer,
                    annealing_length_nt=annealing_length,
                ),
            ),
            reverse_primer=FixedEndpointPrimerPolicy(
                mode=MaterialResolutionMode.FIXED,
                primer=PcrPrimer(
                    oligo=reverse_primer,
                    annealing_length_nt=(
                        primer_annealing_length_nt
                        if primer_annealing_length_nt is not None
                        else len(reverse_primer.sequence_5prime)
                    ),
                ),
            ),
        )
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
        endpoint_auxiliaries=endpoint_auxiliaries,
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
        schema="hop.construction-source/v7",
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
    resolved_adapter_sequence = (
        basal.realizations[0].proximal_adapter_sequence
        if adapter_sequence is None
        else adapter_sequence
    )
    source = _source(
        foldback=foldback.neighborhood.request,
        basal=basal.discovery.request,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        materialization=_materialization(
            adapter=_material(
                "ligation-adapter",
                resolved_adapter_sequence,
            ),
            forward_primer=_material("forward-primer", encoding[:4]),
            reverse_primer=_material(
                "reverse-primer",
                reverse_complement_iupac(encoding[-4:]),
            ),
        ),
    )
    return design, foldback, basal, source


def _selected_partition_inputs(tmp_path: Path):
    payload = _payload().model_copy(
        update={
            "payload": ExactPayload(sequence=PAYLOAD),
            "foldback_boundary": Boundary(offset=len(PAYLOAD)),
        }
    )
    design = _verified_design(tmp_path / "selected-partition", payload=PAYLOAD)
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(
                motif="TCAGATGCTGA",
                cut_offset=0,
                orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
            ),
            _terminus_enzyme(),
            target=FoldbackTarget(
                junction_offset_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=4,
            ),
        ).model_copy(update={"payload": payload})
    )
    basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    )
    encoding = design.plan.hairpin_encoding_insert.sequence
    adapter_sequence = basal.realizations[0].proximal_adapter_sequence
    source = _source(
        foldback=foldback.neighborhood.request,
        basal=basal.discovery.request,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        materialization=_materialization(
            adapter=_material("ligation-adapter", adapter_sequence),
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
    pcr_adapter_sequence = pcr_basal.realizations[0].proximal_adapter_sequence
    pcr_source = _source(
        foldback=pcr_foldback.neighborhood.request,
        basal=pcr_basal.discovery.request,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        materialization=_materialization(
            adapter=_material("ligation-adapter", pcr_adapter_sequence),
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
            adapter=_material("ligation-adapter", clone_adapter),
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
    assert pcr.bundle_id == "hop:construction-bundle/450effe273a2/e5449bc0e9661200"
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


def test_selected_pair_consumes_one_verified_source_partition_receipt(
    tmp_path: Path,
) -> None:
    _, foldback, basal, source = _selected_partition_inputs(tmp_path)
    source_path = _write_source(tmp_path / "selected-partition.yaml", source)
    foldback_receipt = _local_receipt(tmp_path / "foldback.json", foldback)
    basal_receipt = _local_receipt(tmp_path / "basal.json", basal)
    foldback_realization_id = foldback.realizations[0].foldback_realization_id
    basal_realization_id = basal.realizations[0].basal_realization_id
    baseline = construction.compile_construction_from_local_realizations(
        source_path,
        design_bundle_path=tmp_path / "selected-partition" / "design",
        foldback=foldback_receipt,
        foldback_realization_id=foldback_realization_id,
        basal=basal_receipt,
        basal_realization_id=basal_realization_id,
    )
    route = baseline._verified_source().result.realizations[0]
    reaction_enzyme_ids = {
        operation.enzyme_id
        for operation in route.construction_program.reaction_programs[0].stages[0].operations
    }
    enzymes = tuple(
        item
        for request in (source.foldback, source.basal)
        if request is not None
        for item in request.enzyme_provisioning.catalog.enzymes
        if item.enzyme_id in reaction_enzyme_ids
    )
    partition_result = source_partition_for_route(
        payload=source.foldback.payload,
        realization=route,
        enzymes=enzymes,
    )
    partition_path = tmp_path / "source-partition.json"
    partition_path.write_bytes(canonical_json_bytes(partition_result))
    partition = construction.load_verified_source_partition(partition_path)

    compilation = construction.compile_construction_from_local_realizations(
        source_path,
        design_bundle_path=tmp_path / "selected-partition" / "design",
        foldback=foldback_receipt,
        foldback_realization_id=foldback_realization_id,
        basal=basal_receipt,
        basal_realization_id=basal_realization_id,
        source_partition=partition,
        source_partition_realization_id=partition.realization_ids[0],
    )

    result = compilation._verified_source().result
    assert result.source_partition_authority == partition_result
    assert result.accounting.nominal_combinations == 1
    assert result.accounting.valid_realizations == 1
    assert result.realizations[0].source_partition_binding is not None
    output = compilation.write(tmp_path / "partition-bound-construction")
    replayed = construction.load_verified_construction_bundle(output)
    assert replayed.bundle_id == compilation.bundle_id
    assert replayed._verified_source().result.source_partition_authority == partition_result


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


def test_selected_foldback_compiles_a_direct_partition_bound_route(
    tmp_path: Path,
) -> None:
    _, foldback, _, _ = _selected_partition_inputs(tmp_path)
    source = _source(
        foldback=foldback.neighborhood.request,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        materialization=_materialization(),
    )
    source_path = _write_source(tmp_path / "direct-selected.yaml", source)
    foldback_receipt = _local_receipt(tmp_path / "foldback.json", foldback)
    foldback_realization_id = next(
        item.foldback_realization_id
        for item in foldback.realizations
        if len(item.reaction_program.stages) == 1
    )
    baseline = construction.compile_construction_from_local_realizations(
        source_path,
        design_bundle_path=tmp_path / "selected-partition" / "design",
        foldback=foldback_receipt,
        foldback_realization_id=foldback_realization_id,
    )
    route = baseline._verified_source().result.realizations[0]
    reaction_enzyme_ids = {
        operation.enzyme_id
        for operation in route.construction_program.reaction_programs[0].stages[0].operations
    }
    enzymes = tuple(
        item
        for item in source.foldback.enzyme_provisioning.catalog.enzymes
        if item.enzyme_id in reaction_enzyme_ids
    )
    partition_result = source_partition_for_route(
        payload=source.foldback.payload,
        realization=route,
        enzymes=enzymes,
    )
    partition_path = tmp_path / "source-partition.json"
    partition_path.write_bytes(canonical_json_bytes(partition_result))
    partition = construction.load_verified_source_partition(partition_path)

    compilation = construction.compile_construction_from_local_realizations(
        source_path,
        design_bundle_path=tmp_path / "selected-partition" / "design",
        foldback=foldback_receipt,
        foldback_realization_id=foldback_realization_id,
        source_partition=partition,
        source_partition_realization_id=partition.realization_ids[0],
    )

    result = compilation._verified_source().result
    assert compilation.endpoint == ConstructionEndpoint.SSDNA_HAIRPIN.value
    assert compilation.nominal_combinations == 1
    assert compilation.examined_combinations == 1
    assert compilation.valid_realizations == 1
    assert result.realizations[0].source_partition_binding is not None
    request_bytes = canonical_json_bytes(result.request)
    assert b'"selected_foldback_realization_id"' in request_bytes
    assert b'"selected_basal_realization_id"' not in request_bytes
    output = compilation.write(tmp_path / "direct-partition-bound-construction")
    assert construction.load_verified_construction_bundle(output).bundle_id == (
        compilation.bundle_id
    )


def test_selected_direct_route_rejects_a_basal_receipt(tmp_path: Path) -> None:
    _, foldback, basal, _ = _selected_inputs(tmp_path)
    source = _source(
        foldback=foldback.neighborhood.request,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        materialization=_materialization(),
    )

    with pytest.raises(ValueError, match="Direct selected construction must omit basal"):
        construction.compile_construction_from_local_realizations(
            _write_source(tmp_path / "direct-selected.yaml", source),
            design_bundle_path=tmp_path / "selected" / "design",
            foldback=_local_receipt(tmp_path / "foldback.json", foldback),
            foldback_realization_id=foldback.realizations[0].foldback_realization_id,
            basal=_local_receipt(tmp_path / "basal.json", basal),
            basal_realization_id=basal.realizations[0].basal_realization_id,
        )


def test_selected_pcr_route_requires_a_basal_receipt(tmp_path: Path) -> None:
    _, foldback, _, source = _selected_inputs(tmp_path)

    with pytest.raises(ValueError, match="PCR-bearing selected construction requires basal"):
        construction.compile_construction_from_local_realizations(
            _write_source(tmp_path / "pcr-missing-basal.yaml", source),
            design_bundle_path=tmp_path / "selected" / "design",
            foldback=_local_receipt(tmp_path / "foldback.json", foldback),
            foldback_realization_id=foldback.realizations[0].foldback_realization_id,
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
    search = source.foldback.search.model_copy(
        update={"max_search_nodes": source.foldback.search.max_search_nodes + 1}
    )
    mismatched = source.model_copy(
        update={"foldback": source.foldback.model_copy(update={"search": search})}
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
    search = source.basal.search.model_copy(
        update={"max_search_nodes": source.basal.search.max_search_nodes + 1}
    )
    mismatched = source.model_copy(
        update={"basal": source.basal.model_copy(update={"search": search})}
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
