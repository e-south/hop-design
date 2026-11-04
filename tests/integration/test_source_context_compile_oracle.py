"""Ordinary complete construction remains the independent context oracle."""

import json

from hop_design import construction
from hop_design.design.bundle import load_verified_bundle
from hop_design.design.construction.complete import discover_constructions
from hop_design.design.construction.verification import (
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)
from hop_design.kernel.construction.basal.programs import resolve_future_release_action
from hop_design.kernel.construction.release_context import admit_release_contexts
from hop_design.kernel.construction.source_context import admit_source_contexts
from hop_design.models.construction import (
    BasalFutureReleaseRequirement,
    BasalPairAllowance,
    ConstructionEndpoint,
)
from hop_design.models.construction.complete import (
    ConstructionDiscoveryRequest,
    EndpointAuxiliaryPolicy,
    ReleaseSideRequirement,
    TypeIisReleaseRequest,
)
from hop_design.models.construction.complete.source_preparation.policy import (
    SourceDuplexPreparationPolicy,
)
from hop_design.models.construction.product_request import ProductEnds
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from hop_design.models.enzymes import EnzymePermissions
from hop_design.models.molecular_state import StrandEnd
from hop_design.models.physical import SiteOrientation
from tests.contract.test_basal_construction_discovery import _provisioning, _type_iis
from tests.integration.test_complete_construction_clone import _clone_basal_result
from tests.integration.test_complete_construction_discovery import _construction_request
from tests.integration.test_complete_construction_pcr import _foldback, _payload
from tests.unit.test_interface_survey_compact_foldback import _two_method_product


def test_all_complete_contexts_survive_explicit_source_action(tmp_path):
    payload = _payload()
    foldback = _foldback(payload)
    basal = _clone_basal_result(
        payload,
        pairing_allowances=(BasalPairAllowance.MATCH,) * 6,
        nickase_pattern="TTTTTTGA",
        requested_overhang="AAAA",
        payload_end_offset_bp=2,
    )
    assert len(basal.realizations) == 1
    b = basal.realizations[0]
    assert b.source_precursor_sequence == "TCAAAAAA" + payload.payload.sequence
    fp, bp = tmp_path / "foldback.json", tmp_path / "basal.json"
    fp.write_text(foldback.model_dump_json(by_alias=True))
    bp.write_text(basal.model_dump_json(by_alias=True))
    design = load_verified_bundle(
        construction.compile_design_from_local_realizations(
            design_id="cross-boundary-context",
            payload_sequence=payload.payload.sequence,
            endpoint="clone_ready_duplex",
            foldback=construction.load_verified_local_neighborhood(fp),
            foldback_realization_id=foldback.realizations[0].foldback_realization_id,
            basal=construction.load_verified_local_neighborhood(bp),
            basal_realization_id=b.basal_realization_id,
        ).write(tmp_path / "design")
    )
    source = SourceDuplexPreparationPolicy.model_validate_json(
        json.dumps(
            {
                "source_ssdna": {
                    "mode": "constrain",
                    "upstream_sequence_spec": "NGTC",
                    "five_prime_end": "hydroxyl",
                    "three_prime_end": "hydroxyl",
                },
                "forward_primer": {"mode": "derive", "annealing_length_nt": 4},
                "reverse_primer": {"mode": "derive", "annealing_length_nt": 4},
            }
        )
    )
    endpoint = EndpointAuxiliaryPolicy.model_validate_json(
        json.dumps(
            {
                "adapter": {"mode": "constrain", "three_prime_handle_sequence": "GAGACC"},
                "forward_primer": {"mode": "derive", "annealing_length_nt": 4},
                "reverse_primer": {"mode": "derive", "annealing_length_nt": 4},
            }
        )
    )
    left = ReleaseSideRequirement(
        orientation=SiteOrientation.FORWARD,
        cohesive_end_sequence="AAAA",
        overhang_end=StrandEnd.FIVE_PRIME,
        payload_end_offset_bp=2,
    )
    release = TypeIisReleaseRequest(
        enzyme_provisioning=_provisioning(_type_iis(), max_operations=2),
        left=left,
        right=left.model_copy(update={"orientation": SiteOrientation.REVERSE}),
        max_site_pairs=100,
    )
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
        source_preparation=source,
        endpoint_auxiliaries=endpoint,
        release=release,
    ).model_copy(
        update={
            "selected_foldback_realization_id": foldback.realizations[0].foldback_realization_id,
            "selected_basal_realization_id": b.basal_realization_id,
        }
    )
    requirement = BasalFutureReleaseRequirement.model_validate_json(
        json.dumps(
            {
                **left.model_dump(mode="json"),
                "product_end": "left",
                "recognition_material": "source_duplex",
            }
        )
    )
    action = resolve_future_release_action(_type_iis(), requirement)
    assert action is not None
    population = admit_source_contexts(
        policy=source.source_ssdna,
        length_nt=4,
        local_source_sequence=b.source_precursor_sequence,
        payload_boundary_nt=8,
        enzyme=_type_iis(),
        action=action,
        max_decisions=100,
        max_operations=1000,
    )
    assert population.member_at(0) == ("GGTC", 2)
    # Feed the same material/end authorities to the early propagator. The
    # independent complete compiler below still evaluates every original word.
    product = _two_method_product()
    product = product.model_copy(
        update={
            "ends": ProductEnds(left=release.left, right=release.right),
            "materialization": request.materialization,
            "enzyme_catalog": release.enzyme_provisioning.catalog,
            "release": product.release.model_copy(
                update={
                    "enzymes": EnzymePermissions.model_validate(
                        release.enzyme_provisioning.model_dump(exclude={"catalog"})
                    ),
                }
            ),
        }
    )
    early = admit_release_contexts(
        product=product,
        pattern="NGTC",
        local_prefix="TCAAAAAA",
        local_adapter=b.projection.pairing_state.adapter_sequence_5prime,
        nick_offset_nt=8 - b.basal_nick.boundary.offset,
        required_association_nt=b.projection.annealing_obligation.required_annealing_nt,
        limits=DEFAULT_SEQUENCE_LIMITS,
    )
    assert early is not None and early.cardinality == 1
    complete = []
    observations = []
    for first in "ACGT":
        word = first + "GTC"
        data = request.model_dump(mode="json", by_alias=True)
        data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
            word
        )
        exact = ConstructionDiscoveryRequest.model_validate_json(json.dumps(data))
        result = discover_constructions(
            exact,
            foldback=verify_foldback_neighborhood_result(foldback),
            basal=verify_basal_neighborhood_result(basal),
            design=design,
        ).result
        observations.append(
            {
                "context": word,
                "status": result.status.value,
                "failures": result.model_dump(mode="json")["failure_reasons"],
            }
        )
        if result.realizations:
            complete.append(word)
            assert population.sequences.contains(word)
            assert early.contains(word)
    assert complete == ["GGTC"], observations
    (tmp_path / "observations.json").write_text(json.dumps(observations, indent=2) + "\n")
