"""An existential length envelope must preserve complete local variable relations."""

import pytest

from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.kernel.construction import release_population as module
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.support.context_completion import policy
from tests.unit.test_release_length_envelope import with_forward_handle
from tests.unit.test_survey_completion_binding import product


@pytest.fixture(scope="module")
def frames():
    result = {}
    for anneal, gap in ((17, 6), (20, 6), (30, 6), (17, 13), (17, 20)):
        p = product(anneal=anneal, left_gap=gap)
        local = PartitionPlans().get(p).basal
        assert local.supports
        result[anneal, gap] = p, local.supports[0]
    return result


def explicit_union(p, support, base):
    builder = SequenceSetBuilder(
        length_nt=len(support.index.domain.base_domains), max_nodes=10000, max_operations=100000
    )
    root = 0
    for length in range(1, 25):
        relation = module.admit_release_population(
            p, support, policy(base * length), DEFAULT_SEQUENCE_LIMITS
        )
        if relation is None:
            return None
        root = builder.union(root, builder.import_set(relation))
    return builder.freeze(root)


def test_uniform_endpoint_range_evaluates_only_its_maximum(frames, monkeypatch):
    p, support = frames[17, 6]
    original, lengths = module.admit_release_flanks, []

    def measured(product, domains, *args):
        lengths.append(len(domains) - len(support.index.domain.base_domains))
        return original(product, domains, *args)

    monkeypatch.setattr(module, "admit_release_flanks", measured)
    relation = module.admit_release_population(
        p,
        support,
        policy({"min_length_nt": 1, "max_length_nt": 24, "base_spec": "N"}),
        DEFAULT_SEQUENCE_LIMITS,
    )
    assert relation.cardinality > 0
    assert lengths == [24]


@pytest.mark.parametrize("base", tuple("ACGTRYSWKMBDHVN"))
@pytest.mark.parametrize("frame", [(17, 6), (20, 6), (30, 6), (17, 13), (17, 20)])
def test_endpoint_envelope_matches_explicit_union_over_all_local_variables(frames, frame, base):
    p, support = frames[frame]
    expected = explicit_union(p, support, base)
    observed = module.admit_release_population(
        p,
        support,
        policy({"min_length_nt": 1, "max_length_nt": 24, "base_spec": base}),
        DEFAULT_SEQUENCE_LIMITS,
    )
    assert observed == expected


@pytest.mark.parametrize("handle", ["", "G" * 40, "GGTCTC" * 15])
def test_added_forward_handle_retains_individual_lengths(frames, handle, monkeypatch):
    p, support = frames[17, 13]
    p = with_forward_handle(p, handle)
    expected = explicit_union(p, support, "A")
    original, lengths = module.admit_release_flanks, []

    def measured(product, domains, *args):
        lengths.append(len(domains) - len(support.index.domain.base_domains))
        return original(product, domains, *args)

    monkeypatch.setattr(module, "admit_release_flanks", measured)
    observed = module.admit_release_population(
        p,
        support,
        policy({"min_length_nt": 1, "max_length_nt": 24, "base_spec": "A"}),
        DEFAULT_SEQUENCE_LIMITS,
    )
    assert observed == expected
    assert lengths == (list(range(1, 25)) if handle else [24])
