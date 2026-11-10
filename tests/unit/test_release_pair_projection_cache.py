"""Shared projection results retain exact contacts and fresh builder budgets."""

from dataclasses import replace
from random import Random

import pytest

from hop_design.kernel.construction import release_pair_projection as module
from hop_design.kernel.construction.foldback.domains import SequenceVariable
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.models.construction import BasalPairAllowance
from tests.unit.test_release_pair_hidden_cost import unconstrained_contacts


def builder(length=4, *, nodes=10000, operations=100000):
    return SequenceSetBuilder(length_nt=length, max_nodes=nodes, max_operations=operations)


def frame(budget=1):
    domain = unconstrained_contacts(budget)
    masks = (tuple("ACGT"),) * len(domain.base_domains)
    source, adapter = domain.source_span.end.offset - 1, domain.adapter_span.start.offset
    ends = (
        SequenceVariable(source),
        SequenceVariable(adapter),
        SequenceVariable(source, True),
        "A",
    )
    return domain, masks, ends


def test_reuses_exact_results_across_domains_without_sharing_builder_handles(monkeypatch):
    domain, masks, ends = frame()
    original, calls = module.project_end_pairs, []

    def counted(*args):
        calls.append(None)
        return original(*args)

    monkeypatch.setattr(module, "project_end_pairs", counted)
    cache = module.EndPairProjectionCache()
    first = builder()
    expected = first.freeze(cache.project(domain, masks, ends, first))
    # A method's display name cannot affect its already-placed end expression.
    changed = replace(
        domain,
        program=replace(
            domain.program,
            nick_enzyme=domain.program.nick_enzyme.model_copy(
                update={"canonical_name": "Another name"}
            ),
        ),
    )
    second = builder()
    second.from_domains([(base,) for base in "TTTT"])
    assert second.freeze(cache.project(changed, masks, ends, second)) == expected
    assert len(calls) == 1
    separate = module.EndPairProjectionCache()
    third = builder()
    assert third.freeze(separate.project(domain, masks, ends, third)) == expected
    assert len(calls) == 2


def test_shared_results_match_fresh_projection_with_changed_masks_and_permissions():
    cache, rng = module.EndPairProjectionCache(), Random(641)
    for number in range(96):
        domain, masks, ends = frame((0, 1, None)[number % 3])
        masks = list(masks)
        for index in (domain.source_span.end.offset - 1, domain.adapter_span.start.offset):
            masks[index] = tuple(rng.choice(("A", "CG", "GT", "ACGT")))
        contacts = list(domain.target.pairing_constraints)
        contacts[0] = contacts[0].model_copy(
            update={
                "allowed_class": rng.choice(tuple(BasalPairAllowance)),
                "allowed_source_bases": tuple(rng.choice(("A", "CG", "ACGT"))),
                "allowed_adapter_bases": tuple(rng.choice(("T", "GT", "ACGT"))),
            }
        )
        domain = replace(
            domain, target=domain.target.model_copy(update={"pairing_constraints": tuple(contacts)})
        )
        if number % 2:
            ends = ends[::-1]
        reference, actual = builder(), builder()
        expected = reference.freeze(module.project_end_pairs(domain, tuple(masks), ends, reference))
        assert actual.freeze(cache.project(domain, tuple(masks), ends, actual)) == expected


def test_changed_contact_coordinates_and_unbounded_budget_remain_dependencies():
    domain, masks, ends = frame(None)
    source_span = domain.source_span.model_copy(
        update={
            "end": domain.source_span.end.model_copy(
                update={"offset": domain.source_span.end.offset - 1}
            ),
        }
    )
    adapter_span = domain.adapter_span.model_copy(
        update={
            "start": domain.adapter_span.start.model_copy(
                update={"offset": domain.adapter_span.start.offset - 1}
            ),
        }
    )
    cache = module.EndPairProjectionCache()
    for candidate in (
        domain,
        replace(domain, source_span=source_span),
        replace(domain, adapter_span=adapter_span),
    ):
        reference, actual = builder(), builder()
        expected = reference.freeze(module.project_end_pairs(candidate, masks, ends, reference))
        assert actual.freeze(cache.project(candidate, masks, ends, actual)) == expected
    masks = list(masks)
    for position in (0, 1):
        masks[domain.source_span.end.offset - 1 - position] = ("G",)
        masks[domain.adapter_span.start.offset + position] = ("T",)
    for candidate, count in (
        (domain, 1),
        (replace(domain, source_arm_domains=(tuple("ACGT"),)), 0),
    ):
        actual = builder()
        assert (
            actual.freeze(cache.project(candidate, tuple(masks), tuple("AAAA"), actual)).cardinality
            == count
        )


def test_cached_empty_relation_cannot_clear_an_exhausted_builder():
    domain, masks, ends = frame(0)
    masks = list(masks)
    masks[domain.source_span.end.offset - 1], masks[domain.adapter_span.start.offset] = (
        ("G",),
        ("T",),
    )
    cache, first = module.EndPairProjectionCache(), builder()
    assert first.freeze(cache.project(domain, tuple(masks), ends, first)).cardinality == 0
    exhausted = builder(operations=1)
    with pytest.raises(SequenceSetLimitError, match="operation"):
        exhausted.from_domains([tuple("ACGT")] * 4)
    with pytest.raises(SequenceSetLimitError, match="operation"):
        cache.project(domain, tuple(masks), ends, exhausted)


@pytest.mark.parametrize("limits", [{"nodes": 1}, {"operations": 1}])
def test_cache_hit_import_enforces_destination_budgets(limits):
    domain, masks, ends = frame()
    cache, first = module.EndPairProjectionCache(), builder()
    expected = first.freeze(cache.project(domain, masks, ends, first))
    restricted = builder(**limits)
    with pytest.raises(SequenceSetLimitError):
        cache.project(domain, masks, ends, restricted)
    with pytest.raises(SequenceSetLimitError):
        restricted.freeze(0)
    following = builder()
    assert following.freeze(cache.project(domain, masks, ends, following)) == expected


def test_failed_projection_is_not_published(monkeypatch):
    domain, masks, ends = frame()
    cache, calls = module.EndPairProjectionCache(), []
    original = module.project_end_pairs

    def counted(*args):
        calls.append(None)
        return original(*args)

    monkeypatch.setattr(module, "project_end_pairs", counted)
    with pytest.raises(SequenceSetLimitError):
        cache.project(domain, masks, ends, builder(operations=1))
    complete = builder()
    assert complete.freeze(cache.project(domain, masks, ends, complete)).cardinality > 0
    assert len(calls) == 2


def test_eviction_recomputes_the_same_words(monkeypatch):
    monkeypatch.setattr(module, "_MAX_PROJECTIONS", 2)
    domain, masks, _ = frame()
    original, calls = module.project_end_pairs, []

    def counted(*args):
        calls.append(None)
        return original(*args)

    monkeypatch.setattr(module, "project_end_pairs", counted)
    cache = module.EndPairProjectionCache()
    for word in ("AAAA", "CCCC", "GGGG", "AAAA"):
        owner = builder()
        result = owner.freeze(cache.project(domain, masks, tuple(word), owner))
        assert result.cardinality == 1 and result.contains(word)
    assert len(calls) == 4


def test_oversized_value_is_recomputed_without_retention(monkeypatch):
    monkeypatch.setattr(module, "_MAX_PROJECTION_BYTES", 1)
    domain, masks, ends = frame()
    original, calls = module.project_end_pairs, []

    def counted(*args):
        calls.append(None)
        return original(*args)

    monkeypatch.setattr(module, "project_end_pairs", counted)
    cache = module.EndPairProjectionCache()
    expected = None
    for _ in range(2):
        owner = builder()
        result = owner.freeze(cache.project(domain, masks, ends, owner))
        assert expected is None or result == expected
        expected = result
    assert len(calls) == 2
