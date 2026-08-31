"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_route_realization_design.py

Tests exact design compilation from replay-verified local construction results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path

import pytest

import hop_design as hop
import hop_design.construction as construction
from hop_design.design.bundle import load_verified_bundle
from hop_design.design.construction.local_public import LocalNeighborhoodDiscovery
from hop_design.design.construction.verification import (
    ConstructionVerificationError,
    VerifiedFoldbackNeighborhoodResult,
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)
from hop_design.models.construction import (
    BasalPairAllowance,
    ConstructionEndpoint,
    RelaxationCoordinate,
    RelaxationMode,
    RelaxationPolicy,
)
from hop_design.models.junction import Strand
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.models.spec import ExactJunctionDesignSpec
from hop_design.serialization import canonical_json_bytes
from tests.contract.test_foldback_construction_discovery import (
    _nickase,
    _terminus_enzyme,
)
from tests.contract.test_foldback_construction_discovery import (
    _request as foldback_request,
)
from tests.integration.test_complete_construction_discovery import _basal_result, _material
from tests.integration.test_complete_construction_pcr import _foldback, _payload
from tests.integration.test_construction_source_compiler import (
    _materialization,
    _source,
    _write_source,
)


def _receipt(result: object) -> LocalNeighborhoodDiscovery:
    if hasattr(result, "neighborhood"):
        return LocalNeighborhoodDiscovery._create(
            verify_foldback_neighborhood_result(result)  # type: ignore[arg-type]
        )
    return LocalNeighborhoodDiscovery._create(
        verify_basal_neighborhood_result(result)  # type: ignore[arg-type]
    )


def _pcr_authorities():
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    )
    return payload, foldback, basal


def _compile_selected(*, design_id: str = "route-design"):
    payload, foldback, basal = _pcr_authorities()
    return construction.compile_design_from_local_realizations(
        design_id=design_id,
        payload_sequence=payload.payload.sequence,
        endpoint="hairpin_pcr_duplex",
        foldback=_receipt(foldback),
        foldback_realization_id=foldback.realizations[0].foldback_realization_id,
        basal=_receipt(basal),
        basal_realization_id=basal.realizations[0].basal_realization_id,
    )


def test_route_selected_design_compiles_through_the_public_construction_path(
    tmp_path: Path,
) -> None:
    _, foldback, basal = _pcr_authorities()
    compilation = _compile_selected()
    design_path = compilation.write(tmp_path / "design")
    encoding = compilation.plan.hairpin_encoding_insert.sequence
    adapter = next(
        item for item in basal.realizations[0].materials if item.material_id == "ligation-adapter"
    )
    source = _source(
        foldback=foldback.neighborhood.request,
        basal=basal.discovery.request,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        materialization=_materialization(
            adapter=_material(adapter.material_id, adapter.sequence_5prime),
            forward_primer=_material("forward-primer", encoding[:4]),
            reverse_primer=_material(
                "reverse-primer",
                reverse_complement_iupac(encoding[-4:]),
            ),
        ),
    )

    result = construction.compile_construction(
        _write_source(tmp_path / "construction.yaml", source),
        design_bundle_path=design_path,
    )

    assert result.status == "complete"
    assert result.valid_realizations >= 1
    assert result.design_bundle_id == compilation.bundle.bundle_id


def test_each_selected_foldback_alternative_gets_its_own_exact_design() -> None:
    payload = _payload()
    foldback = _receipt(
        __import__(
            "hop_design.design.construction.foldback",
            fromlist=["discover_foldback_neighborhood"],
        ).discover_foldback_neighborhood(
            foldback_request(
                _nickase(),
                _terminus_enzyme(),
                relaxation=RelaxationPolicy(
                    mode=RelaxationMode.THROUGH_RADIUS,
                    max_radius=1,
                    coordinates=(
                        RelaxationCoordinate(
                            name="loop_length_nt",
                            minimum=2,
                            maximum=4,
                        ),
                    ),
                ),
                max_search_nodes=10_000,
                max_realizations=10_000,
            )
        )
    )
    foldback_result = foldback._verified_source()
    alternatives = {item.retained_sequence: item for item in foldback_result.realizations}
    first, second = tuple(alternatives.values())[:2]
    _, _, basal_result = _pcr_authorities()
    basal = _receipt(basal_result)
    basal_id = basal_result.realizations[0].basal_realization_id

    designs = tuple(
        construction.compile_design_from_local_realizations(
            design_id=f"route-design-{index}",
            payload_sequence=payload.payload.sequence,
            endpoint="hairpin_pcr_duplex",
            foldback=foldback,
            foldback_realization_id=item.foldback_realization_id,
            basal=basal,
            basal_realization_id=basal_id,
        )
        for index, item in enumerate((first, second), start=1)
    )

    assert designs[0].plan.hairpin_encoding_insert.sequence != (
        designs[1].plan.hairpin_encoding_insert.sequence
    )
    assert all(item.plan.payload_sequence == payload.payload.sequence for item in designs)


def test_route_design_supports_non_four_base_basal_arms() -> None:
    payload, foldback, _ = _pcr_authorities()
    basal = _basal_result(
        payload,
        pairing_allowances=(BasalPairAllowance.MATCH,) * 3,
        recognition_pattern="TTT",
    )
    selected = basal.realizations[0]

    compilation = construction.compile_design_from_local_realizations(
        design_id="three-base-basal",
        payload_sequence=payload.payload.sequence,
        endpoint="hairpin_pcr_duplex",
        foldback=_receipt(foldback),
        foldback_realization_id=foldback.realizations[0].foldback_realization_id,
        basal=_receipt(basal),
        basal_realization_id=selected.basal_realization_id,
    )

    features = compilation.plan.hairpin_encoding_insert.features
    assert features[0].sequence == selected.projection.pairing_profile.source_sequence_5prime
    assert features[-1].sequence == selected.projection.pairing_profile.adapter_sequence_5prime
    assert len(features[0].sequence) == 3


@pytest.mark.parametrize(
    ("component", "forged_id"),
    (
        ("foldback_junction", "hop:foldback-junction/exact-" + "0" * 64 + "@1"),
        ("basal_junction", "hop:basal-junction/exact-" + "1" * 64 + "@1"),
    ),
)
def test_route_design_rejects_forged_exact_junction_identity(
    component: str,
    forged_id: str,
) -> None:
    spec = _compile_selected().spec.model_dump(mode="python", by_alias=True)
    spec[component]["junction_id"] = forged_id

    with pytest.raises(ValueError, match="content-derived identity"):
        ExactJunctionDesignSpec.model_validate(spec)


def test_route_design_requires_verified_matching_local_authorities() -> None:
    payload, foldback_result, basal_result = _pcr_authorities()
    foldback = _receipt(foldback_result)
    basal = _receipt(basal_result)
    foldback_id = foldback_result.realizations[0].foldback_realization_id
    basal_id = basal_result.realizations[0].basal_realization_id

    with pytest.raises(ValueError, match="PCR-bearing endpoint requires one basal"):
        construction.compile_design_from_local_realizations(
            design_id="missing-basal",
            payload_sequence=payload.payload.sequence,
            endpoint="hairpin_pcr_duplex",
            foldback=foldback,
            foldback_realization_id=foldback_id,
            basal=None,
            basal_realization_id=None,
        )
    with pytest.raises(ValueError, match="does not support the direct endpoint"):
        construction.compile_design_from_local_realizations(
            design_id="direct",
            payload_sequence=payload.payload.sequence,
            endpoint="ssdna_hairpin",
            foldback=foldback,
            foldback_realization_id=foldback_id,
            basal=basal,
            basal_realization_id=basal_id,
        )
    with pytest.raises(ValueError, match="foldback realization was not found"):
        construction.compile_design_from_local_realizations(
            design_id="missing-foldback",
            payload_sequence=payload.payload.sequence,
            endpoint="hairpin_pcr_duplex",
            foldback=foldback,
            foldback_realization_id="hop:foldback-realization/" + "0" * 64 + "@1",
            basal=basal,
            basal_realization_id=basal_id,
        )
    with pytest.raises(ValueError, match="does not match the selected payload"):
        construction.compile_design_from_local_realizations(
            design_id="wrong-payload",
            payload_sequence="GACT",
            endpoint="hairpin_pcr_duplex",
            foldback=foldback,
            foldback_realization_id=foldback_id,
            basal=basal,
            basal_realization_id=basal_id,
        )
    with pytest.raises(ValueError, match="foldback receipt"):
        construction.compile_design_from_local_realizations(
            design_id="wrong-family",
            payload_sequence=payload.payload.sequence,
            endpoint="hairpin_pcr_duplex",
            foldback=basal,
            foldback_realization_id=foldback_id,
            basal=basal,
            basal_realization_id=basal_id,
        )

    forged = object.__new__(LocalNeighborhoodDiscovery)
    forged_verified = object.__new__(VerifiedFoldbackNeighborhoodResult)
    object.__setattr__(
        forged_verified,
        "result",
        foldback_result.model_copy(update={"realizations": ()}),
    )
    object.__setattr__(
        forged,
        "_verified",
        forged_verified,
    )
    object.__setattr__(forged, "_json_bytes", foldback.json_bytes)
    with pytest.raises((ConstructionVerificationError, ValueError)):
        construction.compile_design_from_local_realizations(
            design_id="forged",
            payload_sequence=payload.payload.sequence,
            endpoint="hairpin_pcr_duplex",
            foldback=forged,
            foldback_realization_id=foldback_id,
            basal=basal,
            basal_realization_id=basal_id,
        )


def test_route_design_identity_excludes_local_search_execution_and_round_trips(
    tmp_path: Path,
) -> None:
    payload = _payload()
    first = _foldback(payload)
    wider = __import__(
        "hop_design.design.construction.foldback",
        fromlist=["discover_foldback_neighborhood"],
    ).discover_foldback_neighborhood(
        first.neighborhood.request.model_copy(
            update={
                "enumeration": first.neighborhood.request.enumeration.model_copy(
                    update={"max_search_nodes": 10_000, "max_realizations": 10_000}
                )
            }
        )
    )
    shared_id = first.realizations[0].foldback_realization_id
    assert shared_id in {item.foldback_realization_id for item in wider.realizations}
    _, _, basal_result = _pcr_authorities()
    basal = _receipt(basal_result)
    basal_id = basal_result.realizations[0].basal_realization_id

    compilations = tuple(
        construction.compile_design_from_local_realizations(
            design_id="stable-route-design",
            payload_sequence=payload.payload.sequence,
            endpoint="hairpin_pcr_duplex",
            foldback=_receipt(result),
            foldback_realization_id=shared_id,
            basal=basal,
            basal_realization_id=basal_id,
        )
        for result in (first, wider)
    )

    assert canonical_json_bytes(compilations[0].spec) == canonical_json_bytes(compilations[1].spec)
    assert canonical_json_bytes(compilations[0].plan) == canonical_json_bytes(compilations[1].plan)
    assert compilations[0].bundle == compilations[1].bundle
    design_path = compilations[0].write(tmp_path / "route-design")
    loaded = load_verified_bundle(design_path)
    assert loaded.spec == compilations[0].spec
    assert loaded.plan == compilations[0].plan
    assert loaded.bundle == compilations[0].bundle
    with pytest.raises(ValueError, match="Unsupported HOP spec schema"):
        hop.load_spec(design_path / "hop-spec.json")
