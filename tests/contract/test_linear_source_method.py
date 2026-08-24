from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest
from pydantic import ValidationError

import hop_design as hop
import hop_design.discovery as discovery
import hop_design.methods as methods
from hop_design.models.sequence import reverse_complement_iupac
from tests.support.linear_source_method import (
    HAIRPIN_ENCODING,
    LIGATED,
    SOURCE,
    linear_source_method_request,
)

_request = linear_source_method_request


def test_method_capability_query_reports_every_named_method_without_a_request() -> None:
    assert methods.list_method_capabilities() == (
        methods.MethodCapability(
            method_kind=(methods.MethodKind.LINEAR_SOURCE_MULTINICK_SIZE_SELECTION_HAIRPIN_PCR),
            implementation_status=methods.MethodImplementationStatus.AVAILABLE,
            input_exactness=methods.MethodInputExactness.EXACT_ONLY,
        ),
        methods.MethodCapability(
            method_kind=(
                methods.MethodKind.CIRCULAR_PRECURSOR_EXONUCLEASE_SELECTION_MULTIDIGEST_HAIRPIN_PCR
            ),
            implementation_status=methods.MethodImplementationStatus.UNAVAILABLE,
            input_exactness=methods.MethodInputExactness.NOT_DEFINED,
        ),
    )


def test_method_capability_contract_is_strict_immutable_and_internally_consistent() -> None:
    capability = methods.MethodCapability(
        method_kind=methods.MethodKind.LINEAR_SOURCE_MULTINICK_SIZE_SELECTION_HAIRPIN_PCR,
        implementation_status=methods.MethodImplementationStatus.AVAILABLE,
        input_exactness=methods.MethodInputExactness.EXACT_ONLY,
    )

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        methods.MethodCapability.model_validate(
            {**capability.model_dump(mode="json"), "plugin": "implicit"}
        )
    with pytest.raises(ValidationError, match="Instance is frozen"):
        capability.input_exactness = methods.MethodInputExactness.NOT_DEFINED
    with pytest.raises(ValidationError, match="unavailable method cannot define input exactness"):
        methods.MethodCapability(
            method_kind=(
                methods.MethodKind.CIRCULAR_PRECURSOR_EXONUCLEASE_SELECTION_MULTIDIGEST_HAIRPIN_PCR
            ),
            implementation_status=methods.MethodImplementationStatus.UNAVAILABLE,
            input_exactness=methods.MethodInputExactness.EXACT_ONLY,
        )
    with pytest.raises(ValidationError, match="available method must define input exactness"):
        methods.MethodCapability(
            method_kind=methods.MethodKind.LINEAR_SOURCE_MULTINICK_SIZE_SELECTION_HAIRPIN_PCR,
            implementation_status=methods.MethodImplementationStatus.AVAILABLE,
            input_exactness=methods.MethodInputExactness.NOT_DEFINED,
        )


def test_method_outcome_keeps_availability_and_resolution_orthogonal() -> None:
    available = methods.MethodOutcome(
        implementation_status=methods.MethodImplementationStatus.AVAILABLE,
        resolution_status=methods.MethodResolutionStatus.COMPLETE,
    )
    unavailable = methods.MethodOutcome(
        implementation_status=methods.MethodImplementationStatus.UNAVAILABLE,
        resolution_status=methods.MethodResolutionStatus.NOT_EVALUATED,
    )

    assert (available.implementation_status, available.resolution_status) == (
        "available",
        "complete",
    )
    assert (unavailable.implementation_status, unavailable.resolution_status) == (
        "unavailable",
        "not_evaluated",
    )
    with pytest.raises(ValidationError, match="unavailable method cannot have a resolution"):
        methods.MethodOutcome(
            implementation_status=methods.MethodImplementationStatus.UNAVAILABLE,
            resolution_status=methods.MethodResolutionStatus.COMPLETE,
        )


def test_method_result_outer_schema_rejects_the_retired_plan_v1_container() -> None:
    result = methods.compile_linear_source_multinick_hairpin_pcr(_request())

    assert result.schema_id == "hop.linear-source-multinick-hairpin-pcr-result/v2"
    data = result.model_dump(mode="json", by_alias=True)
    data["schema"] = "hop.linear-source-multinick-hairpin-pcr-result/v1"
    with pytest.raises(ValidationError):
        methods.LinearSourceMultinickHairpinPcrResult.model_validate(data)


def test_multinick_compiler_records_every_cut_and_denatured_fragment() -> None:
    result = methods.compile_linear_source_multinick_hairpin_pcr(_request())

    assert result.method_kind == "linear-source-multinick-size-selection-hairpin-pcr@1"
    assert result.outcome.resolution_status == "complete"
    assert result.plan is not None
    plan = result.plan
    assert [
        (
            site.agent_id,
            site.site_span.start.offset,
            site.site_span.end.offset,
            site.nick.strand,
            site.nick.boundary.offset,
        )
        for site in plan.multi_site_nicked_duplex.sites
    ] == [
        ("example:nicking-agent/bottom-repeat@1", 6, 12, "bottom", 11),
        ("example:nicking-agent/bottom-repeat@1", 18, 24, "bottom", 23),
        ("example:nicking-agent/bottom-repeat@1", 30, 36, "bottom", 35),
        ("example:nicking-agent/top-terminal@1", 56, 63, "top", 58),
    ]
    assert [
        (
            fragment.fragment_id,
            fragment.precursor_strand,
            fragment.precursor_span.start.offset,
            fragment.precursor_span.end.offset,
            fragment.sequence,
            fragment.five_prime_end,
            fragment.three_prime_end,
        )
        for fragment in plan.denatured_fragment_set.fragments
    ] == [
        ("top-0-58", "top", 0, 58, SOURCE[:58], "hydroxyl", "hydroxyl"),
        ("top-58-70", "top", 58, 70, SOURCE[58:], "phosphate", "hydroxyl"),
        (
            "bottom-35-70",
            "bottom",
            35,
            70,
            "CGCAATTGCTGAGGTAATCGAGCTTAACGGTATCC",
            "phosphate",
            "hydroxyl",
        ),
        ("bottom-23-35", "bottom", 23, 35, "TCGTGAGACCTC", "phosphate", "hydroxyl"),
        ("bottom-11-23", "bottom", 11, 23, "TCGTGGGTTAAC", "phosphate", "hydroxyl"),
        ("bottom-0-11", "bottom", 0, 11, "TCGTGATGCAT", "phosphate", "hydroxyl"),
    ]
    assert plan.length_selected_fragment_set.retained_fragment_ids == (
        "top-0-58",
        "bottom-35-70",
    )
    assert plan.length_selected_fragment_set.excluded_fragment_ids == (
        "top-58-70",
        "bottom-23-35",
        "bottom-11-23",
        "bottom-0-11",
    )


def test_annealing_ligation_and_pcr_states_are_strand_aware() -> None:
    result = methods.compile_linear_source_multinick_hairpin_pcr(_request())

    assert result.plan is not None
    plan = result.plan
    pair_counts = dict.fromkeys(hop.JunctionPairKind, 0)
    for pair in plan.adapter_annealed_complex.pairs:
        pair_counts[pair.kind] += 1
    assert pair_counts == {
        hop.JunctionPairKind.WATSON_CRICK: 38,
        hop.JunctionPairKind.GT_WOBBLE: 2,
        hop.JunctionPairKind.HARD_MISMATCH: 0,
    }
    assert [
        (pair.left_index, pair.right_index)
        for pair in plan.adapter_annealed_complex.pairs
        if pair.kind is hop.JunctionPairKind.GT_WOBBLE
    ] == [(21, 13), (33, 1)]
    assert [
        (
            bond.upstream_strand_id,
            bond.upstream_end,
            bond.downstream_strand_id,
            bond.downstream_end,
        )
        for bond in plan.ligated_hairpin.bonds
    ] == [
        ("top-0-58", "three_prime", "bottom-35-70", "five_prime"),
        ("bottom-35-70", "three_prime", "adapter", "five_prime"),
    ]
    assert plan.ligated_hairpin.strand.sequence == LIGATED
    assert len(plan.ligated_hairpin.strand.lineage) == 129
    assert plan.hairpin_pcr_duplex.top_strand.sequence == LIGATED
    assert plan.hairpin_pcr_duplex.bottom_strand.sequence == (
        "TATCGGACTAGGCTAACGTCACAAGAGGTCTCACAAGGATACCGTTAAGCTCGATTACCTCA"
        "GCAATTGCGGGTAATCGAGCTTAACGGTATCCTCGTGAGACCTCTCGTGGGTTAACTCGTGATGCAT"
    )
    assert [
        (binding.primer_id, binding.template_span.start.offset, binding.template_span.end.offset)
        for binding in plan.hairpin_pcr_duplex.primer_bindings
    ] == [
        ("hairpin-fwd", 0, 19),
        ("hairpin-rev", 109, 129),
    ]


def test_declared_kinase_preparation_resolves_unmodified_ligation_ends() -> None:
    result = methods.compile_linear_source_multinick_hairpin_pcr(_request(kinase_step=True))

    assert result.outcome.resolution_status == "complete"
    assert result.plan is not None
    fragments = {item.fragment_id: item for item in result.plan.denatured_fragment_set.fragments}
    assert fragments["bottom-35-70"].five_prime_end == "hydroxyl"
    assert result.plan.materials.ligation_end_preparation == "kinase_step"
    assert len(result.plan.ligated_hairpin.bonds) == 2


def test_restriction_projection_is_destination_neutral_and_matches_the_encoding() -> None:
    result = methods.compile_linear_source_multinick_hairpin_pcr(_request())

    assert result.plan is not None
    product = result.plan.restriction_digest_product
    assert [
        (
            site.site_span.start.offset,
            site.site_span.end.offset,
            site.orientation,
            site.cut.top.offset,
            site.cut.bottom.offset,
        )
        for site in product.sites
    ] == [
        (25, 31, "forward", 32, 36),
        (97, 103, "reverse", 92, 96),
    ]
    assert product.primary_strand.sequence == LIGATED[32:92]
    assert product.complementary_strand.sequence == (
        "CAAGGATACCGTTAAGCTCGATTACCTCAGCAATTGCGGGTAATCGAGCTTAACGGTATC"
    )
    assert product.primary_union_span == hop.Span(
        start=hop.Boundary(offset=32),
        end=hop.Boundary(offset=96),
    )
    assert [
        (
            end.product_end,
            end.protruding_strand_id,
            end.overhang_end,
            end.sequence,
            end.source_span.start.offset,
            end.source_span.end.offset,
            end.primary_cut.offset,
            end.complementary_cut.offset,
        )
        for end in product.cohesive_ends
    ] == [
        ("left", "restriction-primary", "five_prime", LIGATED[32:36], 32, 36, 32, 36),
        (
            "right",
            "restriction-complementary",
            "five_prime",
            reverse_complement_iupac(LIGATED[92:96]),
            92,
            96,
            92,
            96,
        ),
    ]
    assert product.hairpin_encoding_projection.sequence == HAIRPIN_ENCODING
    assert product.destination_readiness == "not_evaluated"


def test_restriction_projection_records_three_prime_cohesive_ends() -> None:
    request = _request()
    restriction_agent = request.restriction_agent.model_copy(
        update={"top_cut_offset": 11, "bottom_cut_offset": 7}
    )

    result = methods.compile_linear_source_multinick_hairpin_pcr(
        request.model_copy(update={"restriction_agent": restriction_agent})
    )

    assert result.plan is not None
    left, right = result.plan.restriction_digest_product.cohesive_ends
    assert (left.protruding_strand_id, left.overhang_end, left.sequence) == (
        "restriction-complementary",
        "three_prime",
        reverse_complement_iupac(LIGATED[32:36]),
    )
    assert (right.protruding_strand_id, right.overhang_end, right.sequence) == (
        "restriction-primary",
        "three_prime",
        LIGATED[92:96],
    )


def test_restriction_product_rejects_cohesive_end_sequence_drift() -> None:
    result = methods.compile_linear_source_multinick_hairpin_pcr(_request())
    assert result.plan is not None
    data = result.plan.restriction_digest_product.model_dump(mode="json")
    data["cohesive_ends"][0]["sequence"] = "AAAA"

    with pytest.raises(ValidationError, match="protruding strand"):
        methods.RestrictionDigestProduct.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("protruding_strand_id", "restriction-complementary"),
        ("overhang_end", "three_prime"),
    ),
)
def test_restriction_product_rejects_cohesive_end_geometry_drift(
    field: str,
    value: str,
) -> None:
    result = methods.compile_linear_source_multinick_hairpin_pcr(_request())
    assert result.plan is not None
    data = result.plan.restriction_digest_product.model_dump(mode="json")
    data["cohesive_ends"][0][field] = value

    with pytest.raises(ValidationError, match="cut geometry"):
        methods.RestrictionDigestProduct.model_validate_json(json.dumps(data))


def test_palindromic_restriction_site_replay_requires_both_orientations() -> None:
    result = methods.compile_linear_source_multinick_hairpin_pcr(_request())
    assert result.plan is not None
    agent = hop.ReleaseAgent(
        agent_id="example:release-agent/palindromic@1",
        motif_top_5to3="AATT",
        top_cut_offset=1,
        bottom_cut_offset=2,
        warning_codes=(),
    )
    sites = discovery.scan_release_agent("AATT", agent=agent)
    product = result.plan.restriction_digest_product.model_copy(
        update={"agent_id": agent.agent_id, "sites": sites}
    )

    product.assert_site_replay("AATT", agent=agent)
    tampered = product.model_copy(update={"sites": (sites[0], sites[0])})
    with pytest.raises(ValueError, match="replay"):
        tampered.assert_site_replay("AATT", agent=agent)


def test_length_selection_fails_closed_when_no_fragment_survives() -> None:
    result = methods.compile_linear_source_multinick_hairpin_pcr(_request(min_length_nt=60))

    assert result.plan is None
    assert result.outcome == methods.MethodOutcome(
        implementation_status=methods.MethodImplementationStatus.AVAILABLE,
        resolution_status=methods.MethodResolutionStatus.INFEASIBLE,
        diagnostics=(
            hop.Diagnostic(
                code="HOP-METHOD-001",
                severity=hop.Severity.ERROR,
                path="fragment_selection",
                message="Length selection did not retain one top and one bottom fragment.",
                evidence={"retained_fragment_ids": []},
                suggestions=("Review the declared length-selection rule.",),
            ),
        ),
    )


def test_method_reports_missing_nick_geometry_as_infeasible() -> None:
    request = _request().model_copy(
        update={
            "nicking_agents": (
                hop.NickingAgent(
                    agent_id="example:nicking-agent/absent@1",
                    motif_top_5to3="CCCCCC",
                    nicked_strand=hop.Strand.BOTTOM,
                    cut_offset=5,
                    warning_codes=(),
                ),
            )
        }
    )

    result = methods.compile_linear_source_multinick_hairpin_pcr(request)

    assert result.plan is None
    assert result.outcome.resolution_status == "infeasible"
    assert result.outcome.diagnostics[0].code == "HOP-METHOD-002"


def test_method_reports_adapter_pairing_outside_declared_bounds() -> None:
    request = _request()
    adapter = request.materials.ligation_adapter
    changed_adapter = adapter.model_copy(update={"sequence": "C" + adapter.sequence[1:]})
    materials = request.materials.model_copy(update={"ligation_adapter": changed_adapter})

    result = methods.compile_linear_source_multinick_hairpin_pcr(
        request.model_copy(update={"materials": materials})
    )

    assert result.plan is None
    assert result.outcome.resolution_status == "infeasible"
    assert result.outcome.diagnostics[0].code == "HOP-METHOD-003"


def test_method_reports_missing_facing_restriction_sites() -> None:
    request = _request().model_copy(
        update={
            "restriction_agent": hop.ReleaseAgent(
                agent_id="example:release-agent/absent@1",
                motif_top_5to3="CCCCCC",
                top_cut_offset=7,
                bottom_cut_offset=11,
                warning_codes=(),
            )
        }
    )

    result = methods.compile_linear_source_multinick_hairpin_pcr(request)

    assert result.plan is None
    assert result.outcome.resolution_status == "infeasible"
    assert result.outcome.diagnostics[0].code == "HOP-METHOD-005"


def test_method_rejects_two_orientations_of_one_palindromic_restriction_span() -> None:
    request = _request().model_copy(
        update={
            "restriction_agent": hop.ReleaseAgent(
                agent_id="example:release-agent/palindromic-single-site@1",
                motif_top_5to3="TGCA",
                top_cut_offset=1,
                bottom_cut_offset=2,
                warning_codes=(),
            )
        }
    )

    result = methods.compile_linear_source_multinick_hairpin_pcr(request)

    assert result.plan is None
    assert result.outcome.resolution_status == "infeasible"
    assert result.outcome.diagnostics[0].code == "HOP-METHOD-005"


def test_method_reports_expected_encoding_disagreement() -> None:
    request = _request().model_copy(update={"expected_hairpin_encoding": "A" * 64})

    result = methods.compile_linear_source_multinick_hairpin_pcr(request)

    assert result.plan is None
    assert result.outcome.resolution_status == "infeasible"
    assert result.outcome.diagnostics[0].code == "HOP-METHOD-006"


@pytest.mark.parametrize(
    "drift",
    (
        "cut",
        "fragment_sequence",
        "terminal_chemistry",
        "pair_index",
        "ligation_bond",
        "primer_boundary",
        "restriction_agent_id",
        "restriction_site_agent_id",
        "restriction_matched_sequence",
        "restriction_site_span",
        "restriction_orientation",
        "restriction_cut",
        "projection",
    ),
)
def test_serialized_method_plan_rejects_cross_state_drift(drift: str) -> None:
    result = methods.compile_linear_source_multinick_hairpin_pcr(_request())
    assert result.plan is not None
    data: Any = result.plan.model_dump(mode="json", by_alias=True)

    if drift == "cut":
        data["multi_site_nicked_duplex"]["sites"][0]["nick"]["boundary"]["offset"] = 12
    elif drift == "fragment_sequence":
        fragment = data["denatured_fragment_set"]["fragments"][0]
        fragment["sequence"] = "C" + fragment["sequence"][1:]
    elif drift == "terminal_chemistry":
        data["denatured_fragment_set"]["fragments"][0]["five_prime_end"] = "phosphate"
    elif drift == "pair_index":
        data["adapter_annealed_complex"]["pairs"][0]["left_index"] = 36
    elif drift == "ligation_bond":
        data["ligated_hairpin"]["bonds"][0]["downstream_strand_id"] = "adapter"
    elif drift == "primer_boundary":
        data["hairpin_pcr_duplex"]["primer_bindings"][1]["template_span"]["start"]["offset"] = 108
    elif drift == "restriction_agent_id":
        data["restriction_digest_product"]["agent_id"] = "example:release-agent/drift@1"
    elif drift == "restriction_site_agent_id":
        data["restriction_digest_product"]["sites"][0]["agent_id"] = "example:release-agent/drift@1"
    elif drift == "restriction_matched_sequence":
        data["restriction_digest_product"]["sites"][0]["matched_sequence"] = "AAAAAA"
    elif drift == "restriction_site_span":
        data["restriction_digest_product"]["sites"][0]["site_span"]["start"]["offset"] = 24
    elif drift == "restriction_orientation":
        data["restriction_digest_product"]["sites"][0]["orientation"] = "reverse"
    elif drift == "restriction_cut":
        data["restriction_digest_product"]["sites"][0]["cut"]["top"]["offset"] = 33
    else:
        projection = data["restriction_digest_product"]["hairpin_encoding_projection"]
        projection["sequence"] = "A" + projection["sequence"][1:]
        projection["sequence_digest"] = (
            "sha256:" + hashlib.sha256(projection["sequence"].encode()).hexdigest()
        )

    with pytest.raises(ValidationError):
        methods.LinearSourceMultinickHairpinPcrPlan.model_validate_json(json.dumps(data))
