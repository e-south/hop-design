"""An explicit source action conditions context without enumerating DNA words."""

import json
from itertools import product
from pathlib import Path

import pytest

from hop_design.kernel.construction.basal.programs import resolve_future_release_action
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.kernel.construction.source_context import admit_source_contexts
from hop_design.models.construction.basal_release import BasalFutureReleaseRequirement
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
)
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.molecular_state import StrandEnd


def inputs(*, gap=0, orientation="forward", specification="NNNN"):
    request = ProductRequest.model_validate_json(
        (Path.cwd() / "examples/complete-construction/product-request.json").read_text()
    )
    enzyme = next(e for e in request.enzyme_catalog.enzymes if e.recognition_pattern == "GGTCTC")
    requirement = BasalFutureReleaseRequirement.model_validate_json(
        json.dumps(
            {
                "product_end": "left",
                "orientation": orientation,
                "cohesive_end_sequence": "AGTC",
                "overhang_end": "five_prime",
                "payload_end_offset_bp": gap,
                "recognition_material": "source_duplex",
            }
        )
    )
    action = resolve_future_release_action(enzyme, requirement)
    assert action is not None
    policy_data = request.materialization.source_preparation.source_ssdna.model_dump(mode="json")
    policy_data.update(mode="constrain", upstream_sequence_spec=specification)
    policy = ConstrainedSourceSsdnaPolicy.model_validate_json(json.dumps(policy_data))
    return policy, enzyme, action


def population(*, local="TCAAGTCACTG", boundary=7, length=4, **kwargs):
    policy, enzyme, action = inputs(**kwargs)
    return admit_source_contexts(
        policy=policy,
        length_nt=length,
        local_source_sequence=local,
        payload_boundary_nt=boundary,
        enzyme=enzyme,
        action=action,
        max_decisions=100,
        max_operations=1000,
    )


@pytest.mark.parametrize("gap", [0, 2])
def test_recognition_crosses_context_boundary_and_keeps_canonical_rank(gap):
    # BsaI GGTCTC(1/5): GGTC + TC A AGTC [gap] | stem.
    # This expectation is written from the enzyme cut map, not the conditioner.
    result = population(
        gap=gap,
        local="TCAAGTC" + "G" * gap + "ACTG",
        boundary=7 + gap,
        specification={"min_length_nt": 3, "max_length_nt": 4, "base_spec": "N"},
    )
    assert result.sequences.cardinality == 1
    assert result.member_at(0) == ("GGTC", 64 + 173)
    for word in map("".join, product("ACGT", repeat=4)):
        assert result.sequences.contains(word) == (word == "GGTC")


def test_fixed_local_conflict_is_empty_not_an_altered_local_sequence():
    assert population(local="GCAAGTCACTG").sequences.cardinality == 0


def test_authored_context_bases_are_not_relaxed():
    assert population(specification="ARTC").sequences.cardinality == 0
    assert population(specification="GRTC").member_at(0) == ("GGTC", 1)


@pytest.mark.parametrize(
    "orientation,gap,pattern",
    [("forward", 0, "NGGTCTCNAGTC"), ("reverse", 7, "NAGTCNGAGACC")],
)
def test_exact_action_in_context_is_compact_and_orientation_specific(orientation, gap, pattern):
    result = population(
        orientation=orientation,
        gap=gap,
        specification="N" * 12,
        local="ACTG",
        boundary=0,
        length=12,
    )
    expected = [
        pattern.replace("N", "{}", 1).replace("N", "{}").format(a, b)
        for a in "ACGT"
        for b in "ACGT"
    ]
    assert result.sequences.cardinality == 16
    assert [result.member_at(i)[0] for i in range(16)] == expected
    assert len(result.sequences.decisions) <= 10


def test_changed_enzyme_definition_cannot_reuse_an_old_action():
    policy, enzyme, action = inputs()
    changed = enzyme.model_copy(update={"canonical_name": "changed-definition"})
    with pytest.raises(ValueError, match="exact enzyme definition"):
        admit_source_contexts(
            policy=policy,
            length_nt=4,
            local_source_sequence="TCAAGTCACTG",
            payload_boundary_nt=7,
            enzyme=changed,
            action=action,
            max_decisions=100,
            max_operations=1000,
        )


@pytest.mark.parametrize("limit", ["max_decisions", "max_operations"])
def test_computing_limit_raises_instead_of_proving_empty(limit):
    policy, enzyme, action = inputs()
    kwargs = {"max_decisions": 100, "max_operations": 1000, limit: 1}
    with pytest.raises(SequenceSetLimitError):
        admit_source_contexts(
            policy=policy,
            length_nt=4,
            local_source_sequence="TCAAGTCACTG",
            payload_boundary_nt=7,
            enzyme=enzyme,
            action=action,
            **kwargs,
        )


def test_huge_context_domain_retains_direct_canonical_addresses():
    result = population(
        specification={"min_length_nt": 23, "max_length_nt": 24, "base_spec": "N"},
        length=24,
        local="ACTG",
        boundary=0,
    )
    assert result.sequences.cardinality == 4**14
    assert len(result.sequences.decisions) == 10
    for ordinal in (0, 1, 1234567, result.sequences.cardinality - 1):
        word, rank = result.member_at(ordinal)
        from hop_design.design.construction.surveys.contexts import source_context_at

        policy, _, _ = inputs(
            specification={"min_length_nt": 23, "max_length_nt": 24, "base_spec": "N"}
        )
        assert source_context_at(policy, rank) == word


def test_incomplete_local_window_is_not_an_empty_certificate():
    with pytest.raises(ValueError, match="window does not contain"):
        population(orientation="reverse", local="A", boundary=0)


def test_variable_capacity_limit_is_not_molecular_exclusion():
    with pytest.raises(SequenceSetLimitError, match="variable capacity"):
        population(specification="N" * 257, length=257)


def test_wholly_local_valid_action_retains_all_contexts():
    result = population(local="GGTCTCAAGTCACTG", boundary=11)
    assert result.sequences.cardinality == 256
    assert result.sequences.decisions == ()
    assert result.member_at(255) == ("TTTT", 255)


def test_site_before_explicit_source_is_empty_only_in_this_frame():
    result = population(local="ACTG", boundary=0)
    assert result.sequences.cardinality == 0


def test_three_prime_word_uses_protruding_strand_convention():
    policy, enzyme, old = inputs()
    # Synthetic polarity reversal retains the same recognition window, but
    # the left word AGTC must appear as GACT on the source reference strand.
    enzyme = enzyme.model_copy(
        update={"cut_offset_reference_strand": 11, "cut_offset_complement_strand": 7}
    )
    requirement = old.requirement.model_copy(update={"overhang_end": StrandEnd.THREE_PRIME})
    action = resolve_future_release_action(enzyme, requirement)
    assert action is not None
    result = admit_source_contexts(
        policy=policy,
        length_nt=4,
        local_source_sequence="TCAGACTACTG",
        payload_boundary_nt=7,
        enzyme=enzyme,
        action=action,
        max_decisions=100,
        max_operations=1000,
    )
    assert result.member_at(0) == ("GGTC", 173)
