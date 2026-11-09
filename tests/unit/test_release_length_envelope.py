"""Uniform source lengths share an exact necessary end-pair envelope."""

import pytest

from hop_design.kernel.construction import release_pair_relation as module
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from hop_design.models.construction.complete.auxiliary.policy import ConstrainedEndpointPrimerPolicy
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.support.context_completion import policy
from tests.unit.test_release_pair_projection import domain
from tests.unit.test_survey_completion_binding import product


def test_uniform_range_without_added_forward_handle_evaluates_only_its_maximum(monkeypatch):
    original, lengths = module._program_relation, []

    def measured(p, d, pattern, *args):
        lengths.append(len(pattern))
        return original(p, d, pattern, *args)

    monkeypatch.setattr(module, "_program_relation", measured)
    result = module.necessary_end_pairs(
        product(),
        (domain(),),
        policy({"min_length_nt": 14, "max_length_nt": 24, "base_spec": "N"}),
        DEFAULT_SEQUENCE_LIMITS,
    )
    assert result.cardinality > 0
    assert lengths == [24]


def with_forward_handle(p, handle):
    auxiliary = p.materialization.endpoint_auxiliaries
    return p.model_copy(
        update={
            "materialization": p.materialization.model_copy(
                update={
                    "endpoint_auxiliaries": auxiliary.model_copy(
                        update={
                            "forward_primer": ConstrainedEndpointPrimerPolicy(
                                mode="constrain",
                                min_annealing_length_nt=14,
                                max_annealing_length_nt=14,
                                five_prime_handle_sequence=handle,
                            )
                        }
                    )
                }
            )
        }
    )


def explicit_union(p, domains, bases):
    builder = SequenceSetBuilder(length_nt=8, max_nodes=10000, max_operations=100000)
    root = 0
    for n in range(1, 25):
        relation = module.necessary_end_pairs(
            p, domains, policy(bases * n), DEFAULT_SEQUENCE_LIMITS
        )
        if relation is None:
            return None
        root = builder.union(root, builder.import_set(relation))
    return builder.freeze(root)


@pytest.mark.parametrize("bases", tuple("ACGTRYSWKMBDHVN"))
@pytest.mark.parametrize("anneal,gap", [(17, 6), (30, 6), (17, 20)])
def test_envelope_equals_explicit_length_union_at_association_and_cut_boundaries(
    bases, anneal, gap
):
    p, domains = product(anneal=anneal, left_gap=gap), (domain(),)
    expected = explicit_union(p, domains, bases)
    observed = module.necessary_end_pairs(
        p,
        domains,
        policy({"min_length_nt": 1, "max_length_nt": 24, "base_spec": bases}),
        DEFAULT_SEQUENCE_LIMITS,
    )
    assert observed == expected


@pytest.mark.parametrize("handle", ["", "G" * 40])
def test_constrained_forward_handle_uses_the_correct_length_envelope(monkeypatch, handle):
    p = with_forward_handle(product(), handle)
    expected = explicit_union(p, (domain(),), "R")
    original, lengths = module._program_relation, []

    def measured(p, d, pattern, *args):
        lengths.append(len(pattern))
        return original(p, d, pattern, *args)

    monkeypatch.setattr(module, "_program_relation", measured)
    result = module.necessary_end_pairs(
        p,
        (domain(),),
        policy({"min_length_nt": 1, "max_length_nt": 24, "base_spec": "R"}),
        DEFAULT_SEQUENCE_LIMITS,
    )
    assert result == expected
    assert lengths == (list(range(1, 25)) if handle else [24])


def test_added_forward_handle_can_make_shorter_lengths_necessary():
    p = with_forward_handle(product(left_gap=13), "GGTCTC" * 15)
    domains = (domain(),)
    expected = explicit_union(p, domains, "A")
    longest = module.necessary_end_pairs(p, domains, policy("A" * 24), DEFAULT_SEQUENCE_LIMITS)
    assert longest.cardinality == 0
    assert expected.cardinality == 1
    observed = module.necessary_end_pairs(
        p,
        domains,
        policy({"min_length_nt": 1, "max_length_nt": 24, "base_spec": "A"}),
        DEFAULT_SEQUENCE_LIMITS,
    )
    assert observed == expected
