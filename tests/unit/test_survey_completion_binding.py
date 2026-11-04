"""Bind auxiliary grouping to exact basal source frames, not input-field names."""

import json

from hop_design.design.construction.surveys.completion.binding import bind_context_completion
from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.unit.test_interface_survey_compact_foldback import _two_method_product


def product(anneal=17, left_gap=6):
    data = _two_method_product().model_dump(mode="json", by_alias=True)
    data["basal"]["geometry"]["minimum_adapter_annealing_nt"] = anneal
    data["ends"]["left"]["payload_end_offset_bp"] = left_gap
    data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = {
        "min_length_nt": 14,
        "max_length_nt": 24,
        "base_spec": "N",
    }
    return ProductRequest.model_validate_json(json.dumps(data))


def bound(p):
    parts = PartitionPlans().get(p)
    assert not parts.empty_local and parts.conflict is None
    return bind_context_completion(p, parts, page=0, limits=DEFAULT_SEQUENCE_LIMITS)


def test_ordinary_frame_keeps_only_length_as_auxiliary_group_when_local_prefix_suffices():
    result = bound(product())
    assert result.protection.scope == "basal_pairing_and_released_insert"
    assert result.protection.protected_suffix_nt == 0
    assert result.plan.group_count == 11


def test_extended_association_preserves_the_context_bases_it_recruits():
    result = bound(product(anneal=20))
    assert result.protection.protected_suffix_nt == 3
    assert result.plan.group_count == 11 * 4**3


def test_interface_reach_can_protect_more_bases_than_association():
    result = bound(product(left_gap=16))
    assert result.protection.protected_suffix_nt == 3
    # Protection still covers three positions, but this exact local source
    # cannot supply the shifted left release site. No completion can repair it.
    assert result.plan.group_count == result.plan.admitted_context_count == 0
    assert result.plan.raw_context_count == sum(4**n for n in range(14, 25))


def test_missing_source_end_frame_retains_every_context_variable():
    p = product()
    data = p.model_dump(mode="json", by_alias=True)
    # Product-end semantics change the source contact frame. The unproved case
    # must preserve its entire exact context rather than reuse the default bound.
    data["release"]["basal_projection"]["product_end"] = "left"
    p = ProductRequest.model_validate_json(json.dumps(data))
    result = bound(p)
    assert result.protection.scope == "all_context_positions"
    assert result.plan.group_count == result.plan.raw_context_count
