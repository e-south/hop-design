"""Compensation branches preserve joint permissions and the invariant stem."""

import json

import pytest

from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.support.survey_navigation import next_page
from tests.unit.test_interface_survey_request import survey_document


def test_branches_cross_only_declared_joint_gaps_with_association_and_nick_options():
    document = survey_document()
    document["basal"]["geometry"]["nick_offsets_nt"] = [0, 2]
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(document))
    branches = SurveyBranches(request)
    assert branches.count == 12  # 2 paired gaps x 2 nicks x 3 association requirements
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=20, release_site_pairs=10)
    products = [branches.product(0, branch=i, limits=limits) for i in range(branches.count)]
    assert all(product.stem_arm == request.stem_arm for product in products)
    assert all(product.ends.left.cohesive_end_sequence == "AAAA" for product in products)
    assert all(product.ends.right.cohesive_end_sequence == "AAAA" for product in products)
    assert {
        (p.ends.left.payload_end_offset_bp, p.ends.right.payload_end_offset_bp) for p in products
    } == {(0, 0), (6, 6)}
    assert {p.basal.geometry.nick_offsets_nt for p in products} == {(0,), (2,)}
    assert {p.basal.geometry.minimum_adapter_annealing_nt for p in products} == {10, 17, 24}
    last = branches.product(65535, branch=0, limits=limits)
    assert last.ends.left.cohesive_end_sequence == "TTTT"
    assert last.ends.right.cohesive_end_sequence == "TTTT"
    assert last.ends.left.orientation.value == "forward"
    assert last.ends.right.orientation.value == "reverse"
    assert last.foldback.search.stop.value == "exhaustive"
    assert last.foldback.search.result_quota is None
    assert last.foldback.search.max_search_nodes == 100


def test_runtime_limits_change_execution_without_changing_branch_or_domain():
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    branches = SurveyBranches(request)
    small = SurveyEvaluationLimits(local_nodes=2, local_realizations=1, release_site_pairs=1)
    large = SurveyEvaluationLimits(local_nodes=1000, local_realizations=80, release_site_pairs=100)
    a = branches.product(27, branch=2, limits=small)
    b = branches.product(27, branch=2, limits=large)
    assert a.ends == b.ends
    assert a.foldback.geometry == b.foldback.geometry
    assert a.basal.geometry == b.basal.geometry
    assert a.materialization == b.materialization
    assert a.foldback.search.max_retained_overhead_nt == b.foldback.search.max_retained_overhead_nt
    for bad in (-1, branches.count, True):
        with pytest.raises(ValueError, match="branch"):
            branches.product(0, branch=bad, limits=small)


def test_joint_gap_roster_broadens_both_ends_before_exhausting_one_side():
    document = survey_document()
    document["placements"] = [
        {"left_bp": left, "right_bp": right} for left in range(3) for right in range(3)
    ]
    document["basal"]["annealing_lengths_nt"] = [17]
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=20, release_site_pairs=10)
    first = [branches.product(0, branch=i, limits=limits) for i in range(3)]
    assert [
        (p.ends.left.payload_end_offset_bp, p.ends.right.payload_end_offset_bp) for p in first
    ] == [(0, 0), (0, 1), (1, 0)]


def test_unrestricted_methods_keep_duplex_release_actions_and_do_not_promote_nickases():
    document = survey_document()
    for family in ("basal", "release"):
        document[family]["enzymes"]["allowed_enzyme_ids"] = []
        document[family]["enzymes"]["role_restrictions"] = []
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(document))
    assert SurveyBranches(request).release_methods == tuple(
        sorted(
            str(e.enzyme_id)
            for e in request.enzyme_catalog.enzymes
            if e.enzyme_class.value == "duplex_restriction"
        )
    )


def test_source_context_permissions_are_addressed_beyond_the_first_assignment():
    document = survey_document()
    document["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "ACGTACAGTCGTAN"
    )
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(document))
    branches = SurveyBranches(request)
    assert branches.count == 24  # six geometry/method branches for each of four contexts
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=20, release_site_pairs=10)
    for ordinal, base in enumerate("ACGT"):
        product = branches.product(0, branch=ordinal * 6, limits=limits)
        assert (
            product.materialization.source_preparation.source_ssdna.upstream_sequence_spec
            == "ACGTACAGTCGTA" + base
        )
        assert product.foldback.geometry == request.foldback.geometry
        assert product.stem_arm == request.stem_arm


def test_source_context_variation_does_not_starve_other_local_sequence_pages():
    from hop_design.design.construction.surveys.partitions import PartitionPlans

    document = survey_document()
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    document["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "ACGTACAGTCGTAN"
    )
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    plans = PartitionPlans()
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=20, release_site_pairs=10)
    # Visit either local population's one-step neighbor, then the next source context,
    # instead of consuming every upstream assignment before any local variation.
    assert next_page(plans, branches, limits, 0, branch=0, page=0) == (0, 1)
    assert next_page(plans, branches, limits, 0, branch=0, page=1) == (0, 2)
    assert next_page(plans, branches, limits, 0, branch=0, page=2) == (1, 0)
    visited = set()
    address = (0, 0)
    while address is not None:
        assert address not in visited
        visited.add(address)
        address = next_page(plans, branches, limits, 0, branch=address[0], page=address[1])
    expected = {
        (branch, page)
        for branch in range(branches.count)
        for page in range(plans.get(branches.product(0, branch=branch, limits=limits)).count)
    }
    assert visited == expected


def test_foldback_geometry_is_addressed_as_coarse_cases_not_a_giant_local_packet():
    document = survey_document()
    document["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[6, 7],
        loop_lengths_nt=[3, 4],
        junction_offsets_nt=[0, 2],
        nick_strand="any",
    )
    document["foldback"]["max_retained_overhead_nt"] = 20
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(document))
    branches = SurveyBranches(request)
    assert branches.geometry_count == 6 * 2 * 2 * 2 * 2
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=10)
    geometries = {
        (
            p.foldback.geometry.annealing_arm_lengths_bp,
            p.foldback.geometry.loop_lengths_nt,
            p.foldback.geometry.junction_offsets_nt,
            p.foldback.geometry.nick_strand.value,
        )
        for i in range(branches.geometry_count)
        for p in (branches.product(0, branch=i, limits=limits),)
    }
    assert geometries == {
        ((arm,), (loop,), (offset,), strand)
        for arm in (6, 7)
        for loop in (3, 4)
        for offset in (0, 2)
        for strand in ("top", "bottom")
    }


def test_geometry_traversal_reaches_admitted_alternatives_and_skips_empty_pages():
    from hop_design.design.construction.surveys.partitions import PartitionPlans

    document = survey_document()
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=10)
    plans = PartitionPlans()
    # The first branch's basal constraints are contradictory: its one diagnostic
    # page must not create a second sequence alternative. Branch 2 does admit
    # alternatives, and reaches its second page before the final coarse branch.
    assert plans.get(branches.product(0, branch=0, limits=limits)).empty_local
    # One association step costs one; moving both released gaps costs two.
    assert next_page(plans, branches, limits, 0, branch=0, page=0) == (1, 0)
    assert next_page(plans, branches, limits, 0, branch=1, page=0) == (3, 0)
    assert next_page(plans, branches, limits, 0, branch=3, page=0) == (2, 0)
    assert next_page(plans, branches, limits, 0, branch=2, page=0) == (2, 1)


def test_coarse_cases_intersect_inherited_hard_scaffold_requirements():
    document = survey_document()
    document["foldback"]["geometry"]["loop_lengths_nt"] = [3, 4]
    document["whole_route_constraints"]["hairpin_scaffold"] = {
        "loop_nt": {"minimum": 3, "maximum": 3},
    }
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    assert {case.loop_length_nt for case in branches.foldback_cases} == {3}


def test_primer_span_preference_keeps_short_cases_but_evaluates_sufficient_spans_first():
    document = survey_document()
    document["foldback"]["geometry"].update(annealing_arm_lengths_bp=[6, 7], loop_lengths_nt=[3])
    document["foldback"]["max_retained_overhead_nt"] = 20
    document["materialization"]["source_preparation"]["reverse_primer"]["annealing_length_nt"] = 14
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    assert [case.annealing_arm_length_bp for case in branches.foldback_cases] == [7, 6]
