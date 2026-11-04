"""Endpoint obligations constrain shared source variables before route compilation."""

from hop_design.kernel.construction.release_context import admit_release_contexts
from hop_design.models.construction.complete.auxiliary.policy import (
    ConstrainedAdapterPolicy,
    ConstrainedEndpointPrimerPolicy,
    DerivedAdapterPolicy,
)
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.unit.test_interface_survey_compact_foldback import _two_method_product


def request(gap=2):
    p = _two_method_product()
    return p.model_copy(
        update={
            "ends": p.ends.model_copy(
                update={
                    side: getattr(p.ends, side).model_copy(
                        update={"payload_end_offset_bp": gap, "cohesive_end_sequence": "AGTC"}
                    )
                    for side in ("left", "right")
                }
            )
        }
    )


def admit(p=None, **overrides):
    values = {
        "product": p or request(),
        "pattern": "N" * 6,
        "local_prefix": "CAAGTCAA",
        "local_adapter": "TTGACT",
        "nick_offset_nt": 0,
        "required_association_nt": 13,
        "limits": DEFAULT_SEQUENCE_LIMITS,
    }
    values.update(overrides)
    return admit_release_contexts(**values)


def test_both_ends_condition_the_same_context_without_expanding_free_handles():
    result = admit(pattern="N" * 24)
    assert result is not None
    assert result.cardinality == 4**19
    assert len(result.decisions) < 40
    assert result.contains("A" * 19 + "GGTCT")
    assert not result.contains("A" * 24)


def test_missing_right_site_excludes_an_entire_context_domain():
    result = admit(
        request(6),
        pattern="N" * 24,
        local_prefix="GGTCTCAAGTCAAAAAA",
        local_adapter="TTTTTTGACTTAAAAAA",
        required_association_nt=17,
    )
    assert result is not None and result.cardinality == 0


def test_authored_iupac_permissions_remain_hard_requirements():
    assert admit(pattern="AGGTCT").cardinality == 1
    assert admit(pattern="AGGTCA").cardinality == 0


def test_primer_and_adapter_handles_can_supply_cross_boundary_footprints():
    p = request()
    auxiliary = p.materialization.endpoint_auxiliaries
    auxiliary = auxiliary.model_copy(
        update={
            "forward_primer": ConstrainedEndpointPrimerPolicy(
                mode="constrain",
                min_annealing_length_nt=2,
                max_annealing_length_nt=2,
                five_prime_handle_sequence="GGT",
            ),
            "adapter": ConstrainedAdapterPolicy(
                mode="constrain", three_prime_handle_sequence="ACC"
            ),
        }
    )
    p = p.model_copy(
        update={
            "materialization": p.materialization.model_copy(
                update={"endpoint_auxiliaries": auxiliary}
            )
        }
    )
    assert admit(p, pattern="CT", required_association_nt=10).cardinality == 1
    auxiliary = auxiliary.model_copy(
        update={
            "adapter": DerivedAdapterPolicy(mode="derive"),
            "reverse_primer": ConstrainedEndpointPrimerPolicy(
                mode="constrain",
                min_annealing_length_nt=2,
                max_annealing_length_nt=2,
                five_prime_handle_sequence="GGT",
            ),
        }
    )
    p = p.model_copy(
        update={
            "materialization": p.materialization.model_copy(
                update={"endpoint_auxiliaries": auxiliary}
            )
        }
    )
    assert admit(p, pattern="CT", required_association_nt=10).cardinality == 1


def test_resource_exhaustion_is_not_molecular_exclusion():
    import pytest

    from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError

    with pytest.raises(SequenceSetLimitError):
        admit(limits=DEFAULT_SEQUENCE_LIMITS.model_copy(update={"max_decisions": 1}))


def test_alternative_enzymes_keep_joint_contexts_not_recombined_base_marginals():
    p = request()
    enzyme = next(e for e in p.enzyme_catalog.enzymes if e.recognition_pattern == "GGTCTC")
    alternative = enzyme.model_copy(
        update={
            "enzyme_id": "example:enzyme/alternative@1",
            "recognition_pattern": "AGCCTC",
        }
    )
    permissions = p.release.enzymes.model_copy(
        update={
            "allowed_enzyme_ids": (enzyme.enzyme_id, alternative.enzyme_id),
            "role_restrictions": (),
        }
    )
    p = p.model_copy(
        update={
            "enzyme_catalog": p.enzyme_catalog.model_copy(
                update={"enzymes": (*p.enzyme_catalog.enzymes, alternative)}
            ),
            "release": p.release.model_copy(update={"enzymes": permissions}),
        }
    )
    result = admit(p)
    assert result.cardinality == 8
    assert result.contains("AGGTCT") and result.contains("AAGCCT")
    assert not result.contains("AAGTCT") and not result.contains("AGGCCT")


def test_untranslated_pairing_policy_falls_back_instead_of_excluding():
    from hop_design.models.construction.targets import BasalPairAllowance, BasalPairConstraint

    p = request()
    auxiliary = p.materialization.endpoint_auxiliaries
    auxiliary = auxiliary.model_copy(
        update={
            "adapter": auxiliary.adapter.model_copy(
                update={
                    "distal_pairing_constraints": (
                        BasalPairConstraint(
                            position_from_ligation=7, allowed_class=BasalPairAllowance.MATCH
                        ),
                    ),
                }
            )
        }
    )
    p = p.model_copy(
        update={
            "materialization": p.materialization.model_copy(
                update={"endpoint_auxiliaries": auxiliary}
            )
        }
    )
    assert admit(p) is None


def test_insufficient_prefix_excludes_without_constructing_invalid_association():
    result = admit(pattern="N", local_prefix="A", local_adapter="ACGT", required_association_nt=4)
    assert result is not None and result.cardinality == 0
