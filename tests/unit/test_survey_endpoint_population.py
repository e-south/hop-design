"""Necessary endpoint admission preserves local authority and exact raw addresses."""

import pytest

from hop_design.design.construction.surveys.completion.population import condition_population
from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.kernel.construction.release_context import admit_release_contexts
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.support.context_completion import policy
from tests.unit.test_survey_completion_binding import product


def conditioned(p, spec="N" * 14, limits=DEFAULT_SEQUENCE_LIMITS):
    local = PartitionPlans().get(p).basal
    return local, condition_population(p, local, policy(spec), limits)


def test_impossible_endpoint_does_not_become_an_empty_local_basal_plane():
    local, filtered = conditioned(product(left_gap=16))
    assert local.parts > 0
    assert filtered.population.parts == 0
    assert filtered.facts()["scope"] == "necessary_endpoint_admission"
    assert filtered.facts()["local_configurations"] == local.parts
    assert local.facts()["scope"] == "local_molecular_admission"


@pytest.mark.parametrize(
    "spec", ["R" * 14, {"min_length_nt": 14, "max_length_nt": 16, "base_spec": "N"}]
)
def test_joint_population_matches_literal_conditions_and_preserves_original_addresses(spec):
    p = product(anneal=20)
    local, filtered = conditioned(p, spec)
    patterns = (spec,) if isinstance(spec, str) else tuple("N" * n for n in range(14, 17))
    expected = set()
    for program, support in enumerate(local.supports):
        for rank in range(support.cardinality):
            member = support.member_at(rank)
            domains = [
                admit_release_contexts(
                    product=p,
                    pattern=pattern,
                    local_prefix=member.source_precursor_sequence[
                        : member.payload_span.start.offset
                    ],
                    local_adapter=member.adapter_sequence,
                    nick_offset_nt=support.index.domain.target.nick_offset_nt,
                    required_association_nt=20,
                    limits=DEFAULT_SEQUENCE_LIMITS,
                )
                for pattern in patterns
            ]
            if any(domain is None or domain.cardinality for domain in domains):
                expected.add((program, support.index.rank_of(member)))
    actual = []
    for rank in range(filtered.population.parts):
        support, member = filtered.population.member_at(rank)
        original = next(i for i, s in enumerate(local.supports) if s.index is support.index)
        raw_rank = support.index.rank_of(member)
        assert support.index.member_at(raw_rank) == member
        selected = filtered.population.select(p, rank)
        assert selected.basal.search.sequence_partition.part_index == raw_rank
        actual.append((original, raw_rank))
    assert len(actual) == len(set(actual))
    assert set(actual) == expected


def test_untranslated_frame_preserves_all_local_candidates():
    p = product()
    p = p.model_copy(
        update={
            "release": p.release.model_copy(
                update={
                    "basal_projection": p.release.basal_projection.model_copy(
                        update={"product_end": "left"}
                    )
                }
            )
        }
    )
    local, filtered = conditioned(p)
    assert filtered.population.parts == local.parts
    assert filtered.facts()["untranslated_programs"] == len(local.supports)


def test_resource_stop_is_not_an_endpoint_exclusion():
    with pytest.raises(SequenceSetLimitError):
        conditioned(
            product(), limits=DEFAULT_SEQUENCE_LIMITS.model_copy(update={"max_decisions": 1})
        )
