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

from hop_design.design.construction.source import compile_construction_source
from hop_design.models.construction import ConstructionEndpoint, SearchCompletionStatus
from hop_design.models.construction.complete import (
    CompositionEnumerationPolicy,
    LinearSourceMaterializationSpec,
    MaterialOrigin,
    PcrPrimer,
    ReleaseSideRequirement,
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
        source_origin=MaterialOrigin.SYNTHESIZED,
        source_five_prime_end=EndChemistry.HYDROXYL,
        source_three_prime_end=EndChemistry.HYDROXYL,
        source_complement_origin=MaterialOrigin.SYNTHESIZED,
        source_complement_five_prime_end=EndChemistry.PHOSPHATE,
        source_complement_three_prime_end=EndChemistry.HYDROXYL,
        adapter=adapter,
        forward_primer=(
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
        reverse_primer=(
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
        schema="hop.construction-source/v3",
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
    assert clone_payload == payload
    assert clone.status == SearchCompletionStatus.COMPLETE.value
    assert clone.endpoint == ConstructionEndpoint.CLONE_READY_DUPLEX.value


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
