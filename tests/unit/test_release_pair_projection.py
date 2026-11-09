"""Projection removes hidden bases without dropping their pairing obligations."""

from collections import Counter
from dataclasses import replace

import pytest

from hop_design.design.construction.basal.traversal import iter_basal_work_units
from hop_design.kernel.construction.basal.domains import (
    BasalSequenceDomain,
    solve_basal_sequence_domain,
)
from hop_design.kernel.construction.foldback.domains import SequenceVariable
from hop_design.kernel.construction.release_pair_projection import project_end_pairs
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from hop_design.models.construction import BasalPairAllowance
from tests.unit.test_survey_completion_binding import product


def domain():
    p = product()
    local = p.construction_source().basal
    for overhead in range(local.search.max_retained_overhead_nt + 1):
        for unit in iter_basal_work_units(local, retained_overhead_nt=overhead):
            result = solve_basal_sequence_domain(
                payload_sequence=unit.payload_sequence,
                target=unit.target,
                endpoint=p.endpoint,
                program=unit.program,
                defer_end_sequence=True,
            )
            if isinstance(result, BasalSequenceDomain):
                return result
    pytest.fail("Expected an admitted basal placement")


@pytest.mark.parametrize("budget", [0, 1])
def test_hidden_mismatch_consumes_budget_without_rebuilding_identical_output_masks(
    monkeypatch, budget
):
    d = domain()
    constraints = tuple(
        c.model_copy(update={"allowed_class": BasalPairAllowance.ANY})
        if c.position_from_ligation == 1
        else c
        for c in d.target.pairing_constraints
    )
    d = replace(
        d,
        target=d.target.model_copy(
            update={"pairing_constraints": constraints, "max_noncanonical_pairs": budget}
        ),
    )
    masks = [tuple("ACGT")] * len(d.base_domains)
    masks[d.source_span.end.offset - 2] = ("A",)
    masks[d.adapter_span.start.offset + 1] = ("A",)
    calls = Counter()
    original = SequenceSetBuilder.from_domains

    def counted(builder, values):
        calls[tuple(tuple(v) for v in values)] += 1
        return original(builder, values)

    monkeypatch.setattr(SequenceSetBuilder, "from_domains", counted)
    builder = SequenceSetBuilder(length_nt=8, max_nodes=1000, max_operations=10000)
    root = project_end_pairs(d, tuple(masks), tuple("ACGTACGT"), builder)
    relation = builder.freeze(root)
    assert relation.cardinality == budget
    assert relation.contains("ACGTACGT") == bool(budget)
    # Every hidden assignment has the same output mask. Construct it once,
    # while its match/mismatch cost still consumes the pairing budget.
    assert max(calls.values()) == 1


@pytest.mark.parametrize("pair", [("A", "A"), ("G", "T")])
def test_unavoidable_hidden_noncanonical_contact_rejects_before_output_factors(monkeypatch, pair):
    d = domain()
    d = replace(
        d,
        target=d.target.model_copy(
            update={
                "pairing_constraints": tuple(
                    c.model_copy(update={"allowed_class": BasalPairAllowance.ANY})
                    for c in d.target.pairing_constraints
                ),
                "max_noncanonical_pairs": 0,
            }
        ),
    )
    masks = [tuple("ACGT")] * len(d.base_domains)
    masks[d.source_span.end.offset - 2] = (pair[0],)
    masks[d.adapter_span.start.offset + 1] = (pair[1],)
    calls = []
    original = SequenceSetBuilder.from_domains

    def counted(builder, values):
        calls.append(values)
        return original(builder, values)

    monkeypatch.setattr(SequenceSetBuilder, "from_domains", counted)
    builder = SequenceSetBuilder(length_nt=8, max_nodes=1000, max_operations=10000)
    assert project_end_pairs(d, tuple(masks), tuple("ACGTACGT"), builder) == 0
    # Validate the output frame once, then reject before constructing contact factors.
    assert len(calls) == 1


def test_impossible_contact_rejects_before_output_factors(monkeypatch):
    d = domain()
    masks = [tuple("ACGT")] * len(d.base_domains)
    masks[d.source_span.end.offset - 1] = ("A",)
    masks[d.adapter_span.start.offset] = ("A",)
    assert d.target.pairing_constraints[0].allowed_class is BasalPairAllowance.MATCH
    calls = []
    original = SequenceSetBuilder.from_domains

    def counted(builder, values):
        calls.append(values)
        return original(builder, values)

    monkeypatch.setattr(SequenceSetBuilder, "from_domains", counted)
    builder = SequenceSetBuilder(length_nt=8, max_nodes=1000, max_operations=10000)
    assert project_end_pairs(d, tuple(masks), tuple("ACGTACGT"), builder) == 0
    assert len(calls) == 1


@pytest.mark.parametrize("budget", [1, 2, None])
@pytest.mark.parametrize("first_pair", [("G", "T"), ("A", "A")])
def test_contact_minimum_sums_hidden_wobble_and_mismatch_without_rejecting_allowed_budget(
    budget, first_pair
):
    d = domain()
    d = replace(
        d,
        target=d.target.model_copy(
            update={
                "pairing_constraints": tuple(
                    c.model_copy(update={"allowed_class": BasalPairAllowance.ANY})
                    for c in d.target.pairing_constraints
                ),
                "max_noncanonical_pairs": budget,
            }
        ),
    )
    masks = [tuple("ACGT")] * len(d.base_domains)
    for position, (source, adapter) in enumerate((first_pair, ("A", "A"))):
        masks[d.source_span.end.offset - 1 - position] = (source,)
        masks[d.adapter_span.start.offset + position] = (adapter,)
    builder = SequenceSetBuilder(length_nt=8, max_nodes=1000, max_operations=10000)
    root = project_end_pairs(d, tuple(masks), tuple("ACGTACGT"), builder)
    assert builder.freeze(root).cardinality == (0 if budget == 1 else 1)


def test_identical_contact_options_are_derived_once_without_merging_positions(monkeypatch):
    from hop_design.kernel.construction import release_pair_projection as module

    d = domain()
    d = replace(
        d,
        target=d.target.model_copy(
            update={
                "pairing_constraints": tuple(
                    c.model_copy(
                        update={
                            "allowed_class": BasalPairAllowance.ANY,
                            "allowed_source_bases": tuple("ACGT"),
                            "allowed_adapter_bases": tuple("ACGT"),
                        }
                    )
                    for c in d.target.pairing_constraints
                ),
                "max_noncanonical_pairs": None,
            }
        ),
    )
    masks = (tuple("ACGT"),) * len(d.base_domains)
    original = module._adapter_domains
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_adapter_domains", counted)
    for attempt in range(2):
        builder = SequenceSetBuilder(length_nt=8, max_nodes=1000, max_operations=10000)
        result = project_end_pairs(d, masks, tuple("ACGTACGT"), builder)
        assert builder.freeze(result).cardinality == 1
        if attempt == 0:
            initial_calls = calls
            assert 0 < initial_calls <= 16
        else:
            assert calls == 2 * initial_calls


@pytest.mark.parametrize(
    ("allowance", "adapters", "expected"),
    [
        (BasalPairAllowance.MATCH, tuple("ACGT"), {"AT", "CG", "GC", "TA"}),
        (BasalPairAllowance.WOBBLE, tuple("ACGT"), {"GT", "TG"}),
        (BasalPairAllowance.MISMATCH, ("A",), {"AA", "CA", "GA"}),
        (BasalPairAllowance.ANY, ("A",), {"AA", "CA", "GA", "TA"}),
    ],
)
def test_contact_options_keep_distinct_class_and_adapter_permissions(allowance, adapters, expected):
    d = domain()
    contacts = tuple(
        c.model_copy(update={"allowed_class": BasalPairAllowance.ANY})
        for c in d.target.pairing_constraints
    )
    contacts = (
        contacts[0],
        contacts[1].model_copy(
            update={
                "allowed_class": allowance,
                "allowed_adapter_bases": adapters,
            }
        ),
        *contacts[2:],
    )
    d = replace(
        d,
        target=d.target.model_copy(
            update={
                "pairing_constraints": contacts,
                "max_noncanonical_pairs": None,
            }
        ),
    )
    masks = (tuple("ACGT"),) * len(d.base_domains)
    ends = (
        SequenceVariable(d.source_span.end.offset - 2),
        SequenceVariable(d.adapter_span.start.offset + 1),
    )
    builder = SequenceSetBuilder(length_nt=2, max_nodes=1000, max_operations=10000)
    result = builder.freeze(project_end_pairs(d, masks, ends, builder))
    assert {result.member_at(i) for i in range(result.cardinality)} == expected
