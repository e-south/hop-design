"""Hidden contacts consume their minimum cost without expanding output decisions."""

from dataclasses import replace
from itertools import product

import pytest

from hop_design.kernel.construction.foldback.domains import SequenceVariable
from hop_design.kernel.construction.release_pair_projection import project_end_pairs
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder
from hop_design.models.construction import BasalPairAllowance
from tests.unit.test_release_pair_projection import domain


def unconstrained_contacts(budget):
    d = domain()
    return replace(
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


def test_all_hidden_contacts_need_only_the_output_decision_budget():
    d = unconstrained_contacts(1)
    masks = [tuple("ACGT")] * len(d.base_domains)
    masks[d.source_span.end.offset - 1] = ("G",)
    masks[d.adapter_span.start.offset] = ("T",)
    # The fixed output needs eight operations. Hidden choices add no output
    # decisions, but the forced wobble must still consume the one allowed cost.
    builder = SequenceSetBuilder(length_nt=8, max_nodes=100, max_operations=8)
    result = builder.freeze(project_end_pairs(d, tuple(masks), tuple("ACGTACGT"), builder))
    assert result.cardinality == 1 and result.contains("ACGTACGT")


def test_zero_remaining_mismatch_budget_builds_only_matched_output_choices():
    d = unconstrained_contacts(1)
    masks = [tuple("ACGT")] * len(d.base_domains)
    source, adapter = d.source_span.end.offset - 1, d.adapter_span.start.offset
    masks[source - 1], masks[adapter + 1] = ("G",), ("T",)
    ends = (SequenceVariable(source), SequenceVariable(adapter))
    builder = SequenceSetBuilder(length_nt=2, max_nodes=100, max_operations=60)
    result = builder.freeze(project_end_pairs(d, tuple(masks), ends, builder))
    assert {result.member_at(i) for i in range(result.cardinality)} == {"AT", "CG", "GC", "TA"}


@pytest.mark.parametrize("budget", [0, 1])
def test_hidden_contacts_keep_unpaired_output_masks_and_copy_aliases(budget):
    d = unconstrained_contacts(budget)
    masks = [tuple("ACGT")] * len(d.base_domains)
    masks[d.source_span.end.offset - 1], masks[d.adapter_span.start.offset] = ("G",), ("T",)
    unpaired = d.payload_span.start.offset
    masks[unpaired] = tuple("AG")
    ends = (SequenceVariable(unpaired), SequenceVariable(unpaired, complemented=True), "A")
    builder = SequenceSetBuilder(length_nt=3, max_nodes=100, max_operations=100)
    result = builder.freeze(project_end_pairs(d, tuple(masks), ends, builder))
    assert {result.member_at(i) for i in range(result.cardinality)} == (
        {"ATA", "GCA"} if budget else set()
    )


@pytest.mark.parametrize("budget", [0, 1, 2, 3, None])
@pytest.mark.parametrize("show_second_adapter", [False, True])
def test_hidden_cost_and_visible_aliases_match_exhaustive_assignments(budget, show_second_adapter):
    d = unconstrained_contacts(budget)
    masks = [tuple("ACGT")] * len(d.base_domains)
    source = d.source_span.end.offset - 1
    adapter = d.adapter_span.start.offset
    # One hidden contact is forced to be noncanonical. The others can match.
    masks[source - 2], masks[adapter + 2] = ("G",), ("T",)
    masks[source], masks[adapter] = tuple("AC"), tuple("GT")
    masks[source - 1], masks[adapter + 1] = tuple("AG"), tuple("CT")
    ends = (
        SequenceVariable(source),
        SequenceVariable(adapter),
        SequenceVariable(source, complemented=True),
        SequenceVariable(adapter + 1 if show_second_adapter else source - 1),
        "A",
    )
    complement = dict(zip("ACGT", "TGCA", strict=True))
    expected = set()
    for a, b, c, e in product(tuple("AC"), tuple("GT"), tuple("AG"), tuple("CT")):
        cost = 1 + (complement[a] != b) + (complement[c] != e)
        if budget is None or cost <= budget:
            expected.add(a + b + complement[a] + (e if show_second_adapter else c) + "A")
    builder = SequenceSetBuilder(length_nt=5, max_nodes=1000, max_operations=10000)
    result = builder.freeze(project_end_pairs(d, tuple(masks), ends, builder))
    assert {result.member_at(i) for i in range(result.cardinality)} == expected
